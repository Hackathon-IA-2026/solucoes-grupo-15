"""Contrato de POST /internal/v1/search no modo real (EMBEDDER=bedrock, issue #69).

Isola Bedrock e o indice vetorial via dependency_overrides (mesmo
padrao de test_index_real.py) - popula o indice diretamente via
POST /internal/v1/index antes de buscar, provando o caminho ponta a
ponta index -> search dentro do proprio servico ai (sem depender do
backend nem do protototipo).
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
from app.vector_store import InMemoryVectorStore
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
    app.dependency_overrides[get_raw_vector_store] = lambda: RawVectorStore(
        tmp_path / "_raw_vectors.jsonl"
    )
    return TestClient(app)


def _index(client: TestClient, document_version: str, text: str, family_id: str) -> None:
    response = client.post(
        "/internal/v1/index",
        json={
            "documents": [
                {
                    "document_version": document_version,
                    "text": text,
                    "family_id": family_id,
                    "corpus_version": "corpus-v1",
                }
            ]
        },
    )
    assert response.status_code == 200


def test_search_returns_real_hits_with_family_id_and_score(client: TestClient) -> None:
    _index(
        client,
        "docver-mmgd",
        "<!-- page:1 -->\nprocure precedentes sobre fiscalização de conexão de MMGD\n",
        "fam-mmgd",
    )
    _index(
        client,
        "docver-outro",
        "<!-- page:1 -->\nassunto completamente diferente, tarifas de energia eólica\n",
        "fam-outro",
    )

    response = client.post(
        "/internal/v1/search",
        json={"query": "procure precedentes sobre fiscalização de conexão de MMGD", "top_k": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == REAL_MODEL_VERSION
    assert len(body["hits"]) >= 1
    hit = body["hits"][0]
    assert set(hit.keys()) == {"family_id", "document_version", "excerpt", "score"}
    # A mesma consulta indexada literalmente deve rankear em primeiro.
    assert hit["family_id"] == "fam-mmgd"


def test_search_respects_top_k(client: TestClient) -> None:
    for i in range(5):
        text = f"<!-- page:1 -->\ntexto do documento numero {i}\n"
        _index(client, f"docver-{i}", text, f"fam-{i}")

    response = client.post("/internal/v1/search", json={"query": "texto qualquer", "top_k": 2})

    assert len(response.json()["hits"]) == 2


def test_search_on_empty_index_returns_no_hits(client: TestClient) -> None:
    response = client.post("/internal/v1/search", json={"query": "consulta sem nada indexado"})

    assert response.status_code == 200
    assert response.json()["hits"] == []
    assert response.json()["model_version"] == REAL_MODEL_VERSION
