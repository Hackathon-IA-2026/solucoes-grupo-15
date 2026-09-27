"""Testes do embedder de vetores pre-computados (issue #88, EMBEDDER=cached).

Dois niveis:

- unidade: ``CachedEmbedder.from_files`` le os dois formatos que ja
  existem no repositorio - JSONL de vetores brutos (issue #73,
  ``app/raw_vectors.py``, com linhas-tombstone) e o JSON de consulta do
  protototipo do Recall@3 (issue #60, ``{"query", "embedding"}``);
- rota: com ``EMBEDDER=cached`` o ai roda o MESMO pipeline real de
  ``EMBEDDER=bedrock`` (chunking + indice vetorial), so trocando a
  origem do vetor - ``get_embedder`` NAO e sobrescrito aqui, e o
  proprio app que monta o embedder a partir de ``EMBEDDING_CACHE_PATHS``.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cached_embeddings import CachedEmbedder, EmbeddingNotCached, get_cached_embedder
from app.chunking import chunk_document
from app.config import get_settings
from app.embeddings import DIMENSIONS
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.main import create_app
from app.raw_vectors import RawVectorStore
from app.routes.index import get_documents_root, get_raw_vector_store, get_vector_store
from app.vector_store import InMemoryVectorStore


def _unit_vector(axis: int) -> list[float]:
    vector = [0.0] * DIMENSIONS
    vector[axis] = 1.0
    return vector


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), "utf-8")
    return path


def test_loads_raw_vector_jsonl_ignoring_tombstones(tmp_path: Path) -> None:
    raw = _write_jsonl(
        tmp_path / "raw.jsonl",
        [
            {"_tombstone": "docver-a"},
            {"chunk_id": "docver-a#chunk-0000", "text": "trecho a", "embedding": _unit_vector(0)},
        ],
    )

    embedder = CachedEmbedder.from_files([raw])

    result = embedder.embed_text("trecho a")
    assert result.vector == _unit_vector(0)
    # Nenhum token e cobrado: o vetor ja existia, nao houve chamada ao Bedrock.
    assert result.input_token_count == 0


def test_loads_query_json_from_recall_prototype(tmp_path: Path) -> None:
    query = tmp_path / "query.json"
    query.write_text(
        json.dumps({"query": "consulta da Carolina", "embedding": _unit_vector(1)}), "utf-8"
    )

    embedder = CachedEmbedder.from_files([query])

    assert embedder.embed_text("consulta da Carolina").vector == _unit_vector(1)


def test_unknown_text_raises_embedding_not_cached(tmp_path: Path) -> None:
    embedder = CachedEmbedder({"conhecido": _unit_vector(0)})

    with pytest.raises(EmbeddingNotCached):
        embedder.embed_text("texto que nunca foi embedado")


def test_rejects_vector_with_wrong_dimensions(tmp_path: Path) -> None:
    raw = _write_jsonl(tmp_path / "raw.jsonl", [{"text": "curto", "embedding": [0.1, 0.2]}])

    with pytest.raises(ValueError, match="dimensoes"):
        CachedEmbedder.from_files([raw])


# ---------------------------------------------------------------------------
# Rotas com EMBEDDER=cached
# ---------------------------------------------------------------------------

_DOC_TEXT = "<!-- page:1 -->\nfiscalizacao de conexao de MMGD pela distribuidora\n"
_QUERY = "precedentes sobre conexao de MMGD"


@pytest.fixture
def cache_file(tmp_path: Path) -> Path:
    chunks = chunk_document(_DOC_TEXT, "docver-mmgd")
    rows = [
        {"chunk_id": chunk.chunk_id, "text": chunk.text, "embedding": _unit_vector(0)}
        for chunk in chunks
    ]
    rows.append({"text": _QUERY, "embedding": _unit_vector(0)})
    return _write_jsonl(tmp_path / "cache.jsonl", rows)


@pytest.fixture
def client(tmp_path: Path, cache_file: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("EMBEDDER", "cached")
    monkeypatch.setenv("EMBEDDING_CACHE_PATHS", str(cache_file))
    get_settings.cache_clear()
    get_cached_embedder.cache_clear()

    app = create_app()
    store = InMemoryVectorStore()
    app.dependency_overrides[get_documents_root] = lambda: tmp_path
    app.dependency_overrides[get_vector_store] = lambda: store
    app.dependency_overrides[get_raw_vector_store] = lambda: RawVectorStore(
        tmp_path / "_raw_vectors.jsonl"
    )
    yield TestClient(app)

    get_settings.cache_clear()
    get_cached_embedder.cache_clear()


def _index(client: TestClient):
    return client.post(
        "/internal/v1/index",
        json={
            "documents": [
                {
                    "document_version": "docver-mmgd",
                    "text": _DOC_TEXT,
                    "family_id": "fam-mmgd",
                    "corpus_version": "corpus-v1",
                }
            ]
        },
    )


def test_cached_mode_indexes_and_searches_with_real_model_version(client: TestClient) -> None:
    index_response = _index(client)
    assert index_response.status_code == 200
    report = index_response.json()["reports"][0]
    assert report["model_version"] == REAL_MODEL_VERSION
    assert report["chunks_indexed"] >= 1

    search_response = client.post("/internal/v1/search", json={"query": _QUERY, "top_k": 3})

    assert search_response.status_code == 200
    body = search_response.json()
    assert body["model_version"] == REAL_MODEL_VERSION
    assert [hit["document_version"] for hit in body["hits"]] == ["docver-mmgd"]


def test_cached_mode_rejects_query_without_precomputed_vector(client: TestClient) -> None:
    response = client.post("/internal/v1/search", json={"query": "consulta nunca embedada"})

    assert response.status_code == 422
    assert "pre-computado" in response.json()["detail"]
