"""Contrato de POST /internal/v1/index no modo real (EMBEDDER=bedrock, issue #69).

Isola Bedrock (FakeBedrockRuntimeClient, ver test_embeddings.py) e o
indice vetorial (InMemoryVectorStore, ver app/vector_store.py) via
dependency_overrides - mesmo padrao ja usado por get_documents_root
(app/routes/index.py). Nenhuma chamada de rede real.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.embeddings import DIMENSIONS, BedrockEmbedder
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.main import create_app
from app.routes.index import get_documents_root, get_embedder, get_vector_store
from app.vector_store import InMemoryVectorStore, index_name_for_model_version
from tests.test_embeddings import FakeBedrockRuntimeClient


@pytest.fixture(autouse=True)
def _bedrock_mode(monkeypatch):
    monkeypatch.setenv("EMBEDDER", "bedrock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@pytest.fixture
def client(tmp_path: Path, store: InMemoryVectorStore) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_documents_root] = lambda: tmp_path
    app.dependency_overrides[get_embedder] = lambda: BedrockEmbedder(FakeBedrockRuntimeClient())
    app.dependency_overrides[get_vector_store] = lambda: store
    return TestClient(app)


def _payload(document_version: str, text: str, **overrides) -> dict:
    doc = {
        "document_version": document_version,
        "text": text,
        "family_id": f"fam-{document_version}",
        "corpus_version": "corpus-v1",
    }
    doc.update(overrides)
    return {"documents": [doc]}


def test_index_chunks_and_embeds_a_document_into_the_vector_store(
    client: TestClient, store: InMemoryVectorStore
) -> None:
    text = "<!-- page:1 -->\nI – DA IDENTIFICAÇÃO\n\n" + ("Texto narrativo de teste. " * 30)
    response = client.post("/internal/v1/index", json=_payload("docver-1", text))

    assert response.status_code == 200
    [report] = response.json()["reports"]
    assert report["document_version"] == "docver-1"
    assert report["model_version"] == REAL_MODEL_VERSION
    assert report["chunks_indexed"] >= 1

    extracted = Path(report["extracted_text_locator"])
    assert extracted.read_text(encoding="utf-8") == text

    index_name = index_name_for_model_version(REAL_MODEL_VERSION)
    assert store.count_chunks_for_document(index_name, "docver-1") == report["chunks_indexed"]


def test_index_is_idempotent_for_same_document_version_and_model_version(
    client: TestClient, store: InMemoryVectorStore
) -> None:
    payload = _payload("docver-2", "<!-- page:1 -->\nTexto único de teste.\n")

    first = client.post("/internal/v1/index", json=payload).json()["reports"][0]
    second = client.post("/internal/v1/index", json=payload).json()["reports"][0]

    assert second == first
    index_name = index_name_for_model_version(REAL_MODEL_VERSION)
    assert store.count_chunks_for_document(index_name, "docver-2") == first["chunks_indexed"]


def test_index_requires_family_id_and_corpus_version_in_real_mode(client: TestClient) -> None:
    payload = {"documents": [{"document_version": "docver-sem-family", "text": "texto qualquer"}]}
    response = client.post("/internal/v1/index", json=payload)

    assert response.status_code == 422


def test_index_writes_1024_dim_embeddings(client: TestClient, store: InMemoryVectorStore) -> None:
    text = "<!-- page:1 -->\nTexto de teste com um único chunk.\n"
    client.post("/internal/v1/index", json=_payload("docver-3", text))

    index_name = index_name_for_model_version(REAL_MODEL_VERSION)
    hits = store.search(index_name, [0.0] * DIMENSIONS, top_k=1)
    assert len(hits) == 1
