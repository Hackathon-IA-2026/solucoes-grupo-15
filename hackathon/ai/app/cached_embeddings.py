"""Embedder de vetores Titan V2 pre-computados (issue #88, ``EMBEDDER=cached``).

Permite rodar o pipeline REAL do ai (chunking + indice vetorial
OpenSearch, o mesmo de ``EMBEDDER=bedrock``) sem credenciais AWS: em
vez de chamar o Bedrock, ``embed_text`` procura o texto exato numa
tabela texto -> vetor carregada de arquivos ja produzidos por execucoes
anteriores com Bedrock real:

- JSONL de vetores brutos da issue #73 (``app/raw_vectors.py``, uma
  linha por chunk com ``text``/``embedding``; linhas-tombstone
  ``{"_tombstone": ...}`` sao ignoradas) - cobre os chunks do corpus;
- JSON de consulta do protototipo do Recall@3 (issue #60,
  ``{"query": ..., "embedding": [...]}``) - cobre o vetor da consulta.

Como os vetores sao os mesmos que o Titan V2 devolveu, ``model_version``
continua sendo ``app.embeddings.MODEL_VERSION``: nao e um modelo novo,
e o mesmo espaco vetorial servido de cache. Texto ausente do cache e
erro explicito (``EmbeddingNotCached`` -> HTTP 422, ver app/main.py),
nunca um vetor inventado - o chunking tem que reproduzir exatamente os
chunks que foram embedados.

Uso previsto: a suite e2e local (``hackathon/tests_e2e/``), que sobe o
ai com ``EMBEDDER=cached`` e ``EMBEDDING_CACHE_PATHS`` apontando para os
arquivos acima.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.embeddings import DIMENSIONS, EmbeddingResult


class EmbeddingNotCached(LookupError):
    """O texto pedido nao tem vetor pre-computado em nenhum arquivo do cache."""

    def __init__(self, text: str) -> None:
        preview = text[:80].replace("\n", " ")
        super().__init__(
            f"texto sem vetor pre-computado em EMBEDDING_CACHE_PATHS (EMBEDDER=cached): "
            f"{preview!r}"
        )


class CachedEmbedder:
    """Mesma superficie de ``BedrockEmbedder`` (``embed_text``), sem rede."""

    def __init__(self, vectors_by_text: dict[str, list[float]]) -> None:
        self._vectors_by_text = vectors_by_text

    @classmethod
    def from_files(cls, paths: list[Path]) -> CachedEmbedder:
        vectors_by_text: dict[str, list[float]] = {}
        for path in paths:
            for text, vector in _read_entries(path):
                if len(vector) != DIMENSIONS:
                    raise ValueError(
                        f"{path}: vetor com {len(vector)} dimensoes, esperado {DIMENSIONS}"
                    )
                vectors_by_text[text] = vector
        return cls(vectors_by_text)

    def embed_text(self, text: str) -> EmbeddingResult:
        vector = self._vectors_by_text.get(text)
        if vector is None:
            raise EmbeddingNotCached(text)
        # Nenhum token de entrada e cobrado: o vetor ja existia.
        return EmbeddingResult(vector=vector, input_token_count=0)


def _read_entries(path: Path) -> Iterator[tuple[str, list[float]]]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        record = json.loads(raw)
        yield record["query"], record["embedding"]
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if "_tombstone" in record:
            continue
        yield record["text"], record["embedding"]


@lru_cache
def get_cached_embedder() -> CachedEmbedder:
    """Carrega o cache uma vez por processo (arquivos de alguns MB)."""
    return CachedEmbedder.from_files(get_settings().embedding_cache_paths)
