"""Indice vetorial do modulo ai (issue #69).

Duas implementacoes do mesmo protocolo ``VectorStore``:

- ``OpenSearchVectorStore``: adapter real, fala com o OpenSearch local
  provisionado pelo docker-compose (``OPENSEARCH_URL``, ver
  app/config.py) via o plugin k-NN embutido na imagem
  ``opensearchproject/opensearch:2.17.0``. E o que roda quando
  ``EMBEDDER=bedrock``.
- ``InMemoryVectorStore``: dublê determinístico usado pelos testes via
  ``dependency_overrides`` (mesmo padrao de ``get_documents_root`` em
  app/routes/index.py) - nao abre nenhuma conexao de rede. Tambem serve
  de referencia executavel do contrato que qualquer adapter futuro
  (ex.: pgvector, citado no contrato de fronteira) precisa cumprir.

Nome do indice (``index_name_for_model_version``): um indice por
``model_version`` - "vetores de modelos diferentes nunca se misturam"
(requirements/contracts/backend-vector-service.md, secao "Operacoes do
port"). Trocar de modelo troca de indice inteiro, nunca mistura
vetores de dimensoes/normalizacoes diferentes numa mesma busca.
``reindex`` (app/routes/reindex.py) apaga e recria esse indice do zero.

Forma de ``ChunkDoc``/``ScoredChunk`` e deliberadamente estavel para a
issue #73 (indexacao do corpus completo): mais documentos/chunks so
significam mais chamadas a ``index_chunks``, nunca mudanca de forma.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


def index_name_for_model_version(model_version: str) -> str:
    """Nome de indice OpenSearch valido e estavel para um model_version.

    Nomes de indice OpenSearch/Elasticsearch precisam ser minusculos e
    sem caracteres especiais alem de ``-``/``_``/``.`` - normaliza
    qualquer outro caractere para ``-``.
    """
    slug = re.sub(r"[^a-z0-9._-]", "-", model_version.lower())
    return f"capiwatt-chunks-{slug}"


@dataclass(frozen=True)
class ChunkDoc:
    """Um chunk a gravar no indice - a unidade de indexacao/busca."""

    chunk_id: str
    document_version: str
    family_id: str
    corpus_version: str
    model_version: str
    section: str | None
    page_start: int | None
    page_end: int | None
    text: str
    embedding: list[float]


@dataclass(frozen=True)
class ScoredChunk:
    """Um hit cru de busca - mesma forma que app/routes/search.py::SearchHitOut
    espera (family_id, document_version, excerpt, score)."""

    chunk_id: str
    document_version: str
    family_id: str
    excerpt: str
    score: float


class VectorStore(Protocol):
    """Port minimo que qualquer backend de indice vetorial precisa cumprir.

    Contrato de idempotencia: chamar ``index_chunks`` de novo com um
    ``ChunkDoc`` de mesmo ``chunk_id`` sobrescreve o chunk (upsert por
    id), nunca duplica - e o que da a ``index`` idempotencia por
    (document_version, model_version) na camada de armazenamento, junto
    do cache em memoria de app/routes/index.py.
    """

    def ensure_index(self, index_name: str, dimensions: int) -> None: ...

    def index_chunks(self, index_name: str, chunks: list[ChunkDoc]) -> None: ...

    def delete_document(self, index_name: str, document_version: str) -> None: ...

    def delete_index(self, index_name: str) -> None: ...

    def count_chunks_for_document(self, index_name: str, document_version: str) -> int: ...

    def search(
        self, index_name: str, query_vector: list[float], top_k: int
    ) -> list[ScoredChunk]: ...


class InMemoryVectorStore:
    """Dublê em memoria do indice vetorial - usado nos testes (issue #69).

    Busca por forca bruta (produto escalar - vetores Titan V2 sao
    normalizados, entao produto escalar == cosseno, mesma escolha do
    protototipo do Recall@3). Suficiente para o volume de teste (dezenas
    de chunks); nao e o que roda em produção.
    """

    def __init__(self) -> None:
        self._indices: dict[str, dict[str, ChunkDoc]] = {}

    def ensure_index(self, index_name: str, dimensions: int) -> None:
        self._indices.setdefault(index_name, {})

    def index_chunks(self, index_name: str, chunks: list[ChunkDoc]) -> None:
        docs = self._indices.setdefault(index_name, {})
        for chunk in chunks:
            docs[chunk.chunk_id] = chunk

    def delete_document(self, index_name: str, document_version: str) -> None:
        docs = self._indices.get(index_name, {})
        for chunk_id in [cid for cid, c in docs.items() if c.document_version == document_version]:
            del docs[chunk_id]

    def delete_index(self, index_name: str) -> None:
        self._indices.pop(index_name, None)

    def count_chunks_for_document(self, index_name: str, document_version: str) -> int:
        docs = self._indices.get(index_name, {})
        return sum(1 for c in docs.values() if c.document_version == document_version)

    def search(self, index_name: str, query_vector: list[float], top_k: int) -> list[ScoredChunk]:
        docs = self._indices.get(index_name, {})
        scored = [
            (
                sum(x * y for x, y in zip(query_vector, chunk.embedding, strict=True)),
                chunk,
            )
            for chunk in docs.values()
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            ScoredChunk(
                chunk_id=chunk.chunk_id,
                document_version=chunk.document_version,
                family_id=chunk.family_id,
                excerpt=chunk.text,
                score=score,
            )
            for score, chunk in scored[:top_k]
        ]


class OpenSearchVectorStore:
    """Adapter real - OpenSearch local via plugin k-NN (issue #69).

    ``opensearch_url`` vem de ``Settings.opensearch_url``
    (app/config.py, default ``http://opensearch:9200``, ja wired no
    docker-compose.yml). Sem seguranca (``DISABLE_SECURITY_PLUGIN=true``
    no compose) - sem usuario/senha aqui de proposito, so para o
    ambiente local do hackathon.
    """

    def __init__(self, opensearch_url: str) -> None:
        from opensearchpy import OpenSearch

        self._client = OpenSearch(hosts=[opensearch_url])

    def ensure_index(self, index_name: str, dimensions: int) -> None:
        if self._client.indices.exists(index=index_name):
            return
        self._client.indices.create(
            index=index_name,
            body={
                "settings": {"index": {"knn": True}},
                "mappings": {
                    "properties": {
                        "document_version": {"type": "keyword"},
                        "family_id": {"type": "keyword"},
                        "corpus_version": {"type": "keyword"},
                        "model_version": {"type": "keyword"},
                        "section": {"type": "text"},
                        "page_start": {"type": "integer"},
                        "page_end": {"type": "integer"},
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": dimensions,
                            "method": {
                                "name": "hnsw",
                                "space_type": "innerproduct",
                                "engine": "nmslib",
                            },
                        },
                    }
                },
            },
        )

    def index_chunks(self, index_name: str, chunks: list[ChunkDoc]) -> None:
        from opensearchpy import helpers

        actions = [
            {
                "_op_type": "index",
                "_index": index_name,
                "_id": chunk.chunk_id,
                "_source": {
                    "document_version": chunk.document_version,
                    "family_id": chunk.family_id,
                    "corpus_version": chunk.corpus_version,
                    "model_version": chunk.model_version,
                    "section": chunk.section,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "text": chunk.text,
                    "embedding": chunk.embedding,
                },
            }
            for chunk in chunks
        ]
        if actions:
            helpers.bulk(self._client, actions, refresh=True)

    def delete_document(self, index_name: str, document_version: str) -> None:
        if not self._client.indices.exists(index=index_name):
            return
        self._client.delete_by_query(
            index=index_name,
            body={"query": {"term": {"document_version": document_version}}},
            refresh=True,
        )

    def delete_index(self, index_name: str) -> None:
        if self._client.indices.exists(index=index_name):
            self._client.indices.delete(index=index_name)

    def count_chunks_for_document(self, index_name: str, document_version: str) -> int:
        if not self._client.indices.exists(index=index_name):
            return 0
        result = self._client.count(
            index=index_name,
            body={"query": {"term": {"document_version": document_version}}},
        )
        return int(result["count"])

    def search(self, index_name: str, query_vector: list[float], top_k: int) -> list[ScoredChunk]:
        if not self._client.indices.exists(index=index_name):
            return []
        response = self._client.search(
            index=index_name,
            body={
                "size": top_k,
                "query": {"knn": {"embedding": {"vector": query_vector, "k": top_k}}},
            },
        )
        hits = response.get("hits", {}).get("hits", [])
        return [
            ScoredChunk(
                chunk_id=hit["_id"],
                document_version=hit["_source"]["document_version"],
                family_id=hit["_source"]["family_id"],
                excerpt=hit["_source"]["text"],
                score=hit["_score"],
            )
            for hit in hits
        ]
