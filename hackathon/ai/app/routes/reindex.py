"""Rota interna de reindexacao do modulo ai (issue #69).

Cobre a operacao ``reindex(corpus_version)`` do port VectorService
(requirements/contracts/backend-vector-service.md: "delete/reindex
existem porque troca de modelo de embeddings exige reindexar; vetores
de modelos diferentes nunca se misturam").

Interface: mesma forma de ``POST /internal/v1/index`` (mesmo
``IndexRequest``/``IndexResponse`` - ver app/routes/index.py) - o
backend (dono do catalogo) chama esta rota reenviando todo o catalogo
atual (os mesmos documentos que enviaria a ``index``, com o mesmo texto
ja extraido que ja tem guardado). O ``ai`` nunca le o catalogo do
backend diretamente (divisao de posse do contrato de fronteira) - ele
so reconstroi a partir do que o backend reenvia nesta chamada.

Efeito: ignora o cache de idempotencia e o conteudo anterior do indice
para o ``model_version`` corrente - apaga o indice OpenSearch inteiro
(modo ``EMBEDDER=bedrock``) ou limpa as entradas do cache em memoria
(modo ``EMBEDDER=fake``) e reprocessa cada documento recebido do zero,
mesmo que (document_version, model_version) já tivesse um relatorio
cacheado antes desta chamada.

Esta e a interface que a issue #73 (indexacao do corpus completo) vai
reusar sem redesenho: reindexar um corpus maior e so enviar mais
documentos no mesmo ``documents[]``, nada na forma muda.
"""

from pathlib import Path

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.embeddings import BedrockEmbedder
from app.raw_vectors import RawVectorStore
from app.routes.index import (
    MODEL_VERSION,
    IndexReport,
    IndexRequest,
    IndexResponse,
    _index_one_fake,
    _index_one_real,
    get_documents_root,
    get_embedder,
    get_index_store,
    get_raw_vector_store,
    get_vector_store,
)
from app.vector_store import VectorStore, index_name_for_model_version

router = APIRouter(prefix="/internal/v1", tags=["internal"])


@router.post("/reindex", response_model=IndexResponse)
def reindex_documents(
    payload: IndexRequest,
    documents_root: Path = Depends(get_documents_root),
    store: dict[tuple[str, str], IndexReport] = Depends(get_index_store),
    embedder: BedrockEmbedder = Depends(get_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
    raw_vector_store: RawVectorStore = Depends(get_raw_vector_store),
) -> IndexResponse:
    settings = get_settings()

    if settings.embedder == "bedrock":
        index_name = index_name_for_model_version(REAL_MODEL_VERSION)
        vector_store.delete_index(index_name)
        raw_vector_store.delete_all()
        _clear_cache_for_model_version(store, REAL_MODEL_VERSION)
        reports = [
            _index_one_real(
                document,
                documents_root,
                store,
                embedder,
                vector_store,
                raw_vector_store,
                force=True,
            )
            for document in payload.documents
        ]
    else:
        _clear_cache_for_model_version(store, MODEL_VERSION)
        reports = [
            _index_one_fake(document, documents_root, store) for document in payload.documents
        ]

    return IndexResponse(reports=reports)


def _clear_cache_for_model_version(
    store: dict[tuple[str, str], IndexReport], model_version: str
) -> None:
    for key in [k for k in store if k[1] == model_version]:
        del store[key]
