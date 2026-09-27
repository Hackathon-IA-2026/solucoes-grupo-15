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
from app.vector_store import ChunkDoc, InMemoryVectorStore, index_name_for_model_version
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
    assert set(hit.keys()) == {
        "family_id",
        "document_version",
        "chunk_id",
        "chunk_index",
        "excerpt",
        "score",
    }
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


def test_search_hit_carries_the_stable_chunk_id_and_its_index_in_the_document(
    client: TestClient, store: InMemoryVectorStore
) -> None:
    """Issue #96: cada hit carrega o ``chunk_id`` gravado no indice e o
    indice real do chunk dentro do documento - nunca a posicao do hit na
    lista. Aqui o chunk 3 de ``docver-x`` rankeia em primeiro (posicao 0)."""
    query = "fiscalizacao de conexao de MMGD"
    query_vector = BedrockEmbedder(FakeBedrockRuntimeClient()).embed_text(query).vector
    orthogonal = [0.0] * len(query_vector)
    orthogonal[0] = 1.0
    store.index_chunks(
        index_name_for_model_version(REAL_MODEL_VERSION),
        [
            ChunkDoc(
                chunk_id=f"docver-x#chunk-{i:04d}",
                document_version="docver-x",
                family_id="fam-x",
                corpus_version="corpus-v1",
                model_version=REAL_MODEL_VERSION,
                section=None,
                page_start=1,
                page_end=1,
                text=f"trecho {i}",
                embedding=query_vector if i == 3 else orthogonal,
            )
            for i in range(5)
        ],
    )

    response = client.post("/internal/v1/search", json={"query": query, "top_k": 2})

    assert response.status_code == 200
    top = response.json()["hits"][0]
    assert top["chunk_id"] == "docver-x#chunk-0003"
    assert top["chunk_index"] == 3
    assert top["excerpt"] == "trecho 3"
