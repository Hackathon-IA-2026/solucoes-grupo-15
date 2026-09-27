"""Contrato de POST /internal/v1/reindex (issue #69, AC "reindex(corpus_version)
reconstrói o índice do zero a partir do catálogo").

Prova, nos dois modos (fake e bedrock), que reindexar reconstroi do
zero: mesmo com um relatorio ja cacheado por (document_version,
model_version), reindex reprocessa e, no modo real, o indice vetorial
reflete exatamente os documentos reenviados (nada do que existia antes
sobrevive se nao foi reenviado).
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.embeddings import BedrockEmbedder
from app.main import create_app
from app.raw_vectors import RawVectorStore
from app.routes.index import (
    get_documents_root,
    get_embedder,
    get_raw_vector_store,
    get_vector_store,
)
from app.vector_store import InMemoryVectorStore, index_name_for_model_version
from tests.test_embeddings import FakeBedrockRuntimeClient


@pytest.mark.no_bedrock_mode
def test_reindex_fake_mode_reprocesses_even_when_cached(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_documents_root] = lambda: tmp_path
    client = TestClient(app)

    payload = {"documents": [{"document_version": "docver-1", "text": "bloco unico"}]}
    client.post("/internal/v1/index", json=payload)

    reindexed_payload = {
        "documents": [{"document_version": "docver-1", "text": "bloco um\n\nbloco dois"}]
    }
    response = client.post("/internal/v1/reindex", json=reindexed_payload)

    assert response.status_code == 200
    [report] = response.json()["reports"]
    assert report["chunks_indexed"] == 2
    extracted = Path(report["extracted_text_locator"])
    assert extracted.read_text(encoding="utf-8") == "bloco um\n\nbloco dois"


@pytest.fixture(autouse=True)
def _bedrock_mode(monkeypatch, request):
    if "no_bedrock_mode" in request.keywords:
        yield
        return
    monkeypatch.setenv("EMBEDDER", "bedrock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client(tmp_path: Path, store: InMemoryVectorStore) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_documents_root] = lambda: tmp_path
    app.dependency_overrides[get_embedder] = lambda: BedrockEmbedder(FakeBedrockRuntimeClient())
    app.dependency_overrides[get_vector_store] = lambda: store
    app.dependency_overrides[get_raw_vector_store] = lambda: RawVectorStore(
        tmp_path / "_raw_vectors.jsonl"
    )
    return TestClient(app)


def test_reindex_real_mode_rebuilds_index_from_scratch(tmp_path: Path) -> None:
    store = InMemoryVectorStore()
    client = _client(tmp_path, store)
    index_name = index_name_for_model_version(REAL_MODEL_VERSION)

    doc_a = {
        "document_version": "docver-a",
        "text": "<!-- page:1 -->\ntexto do documento A\n",
        "family_id": "fam-a",
        "corpus_version": "corpus-v1",
    }
    doc_b = {
        "document_version": "docver-b",
        "text": "<!-- page:1 -->\ntexto do documento B\n",
        "family_id": "fam-b",
        "corpus_version": "corpus-v1",
    }
    client.post("/internal/v1/index", json={"documents": [doc_a, doc_b]})
    assert store.count_chunks_for_document(index_name, "docver-a") >= 1
    assert store.count_chunks_for_document(index_name, "docver-b") >= 1

    # Reindex so com o documento A: o indice reconstruido do zero nao deve
    # conter nenhum resto do documento B (que nao foi reenviado).
    response = client.post("/internal/v1/reindex", json={"documents": [doc_a]})

    assert response.status_code == 200
    assert store.count_chunks_for_document(index_name, "docver-a") >= 1
    assert store.count_chunks_for_document(index_name, "docver-b") == 0


def test_reindex_real_mode_also_rebuilds_raw_vectors(tmp_path: Path) -> None:
    """Os vetores brutos (fora do indice, issue #73/I7) seguem a mesma
    reconstrucao do zero que o indice OpenSearch."""
    store = InMemoryVectorStore()
    client = _client(tmp_path, store)

    doc_a = {
        "document_version": "docver-a",
        "text": "<!-- page:1 -->\ntexto do documento A\n",
        "family_id": "fam-a",
        "corpus_version": "corpus-v1",
    }
    doc_b = {
        "document_version": "docver-b",
        "text": "<!-- page:1 -->\ntexto do documento B\n",
        "family_id": "fam-b",
        "corpus_version": "corpus-v1",
    }
    client.post("/internal/v1/index", json={"documents": [doc_a, doc_b]})
    client.post("/internal/v1/reindex", json={"documents": [doc_a]})

    raw_store = RawVectorStore(tmp_path / "_raw_vectors.jsonl")
    remaining = raw_store.load_all()
    assert {c.document_version for c in remaining} == {"docver-a"}


def test_reindex_real_mode_reprocesses_changed_text_despite_cache(tmp_path: Path) -> None:
    store = InMemoryVectorStore()
    client = _client(tmp_path, store)
    index_name = index_name_for_model_version(REAL_MODEL_VERSION)

    doc_v1 = {
        "document_version": "docver-x",
        "text": "<!-- page:1 -->\ntexto original\n",
        "family_id": "fam-x",
        "corpus_version": "corpus-v1",
    }
    client.post("/internal/v1/index", json={"documents": [doc_v1]})
    original_count = store.count_chunks_for_document(index_name, "docver-x")

    doc_v2 = {**doc_v1, "text": "<!-- page:1 -->\n" + ("texto bem mais longo e diferente. " * 400)}
    client.post("/internal/v1/reindex", json={"documents": [doc_v2]})

    new_count = store.count_chunks_for_document(index_name, "docver-x")
    assert new_count > original_count
    hits = store.search(index_name, [0.0] * 1024, top_k=10)
    assert all(h.document_version == "docver-x" for h in hits)
    assert len(hits) == new_count
