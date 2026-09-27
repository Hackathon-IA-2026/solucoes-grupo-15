"""Contrato de GET /internal/v1/families/{family_id}/similar (issue #92).

``similar_families(family_id, top_k) -> [{family_id, score}]`` e a
vizinhanca vetorial entre familias (d14-data-operations-modeling): o
vetor de cada familia e a media dos embeddings dos seus chunks,
renormalizada (mesma agregacao calibrada nas issues #61/#74), e o score
e o produto interno entre vetores de familia. O ai so entrega
candidatos - aplicar ``limiar_relacao``/``limiar_fusao`` e gravar
arestas e do backend.

O indice e populado direto no ``InMemoryVectorStore`` com vetores de
3 dimensoes escolhidos a mao, para que os scores esperados sejam
literais calculados no papel, nao recomputados pelo teste.
"""

import math

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.main import create_app
from app.routes.index import get_vector_store
from app.vector_store import ChunkDoc, InMemoryVectorStore, index_name_for_model_version

INDEX = index_name_for_model_version(REAL_MODEL_VERSION)
HALF_SQRT2 = math.sqrt(2) / 2  # 0.7071...


def _chunk(family_id: str, n: int, embedding: list[float]) -> ChunkDoc:
    document_version = f"{family_id}-v1"
    return ChunkDoc(
        chunk_id=f"{document_version}#chunk-{n:04d}",
        document_version=document_version,
        family_id=family_id,
        corpus_version="corpus-v1",
        model_version=REAL_MODEL_VERSION,
        section=None,
        page_start=1,
        page_end=1,
        text=f"trecho {n} de {family_id}",
        embedding=embedding,
    )


@pytest.fixture
def store() -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    store.ensure_index(INDEX, 3)
    store.index_chunks(
        INDEX,
        [
            # fam-a: media de (1,0,0) e (0,1,0) -> (1/sqrt2, 1/sqrt2, 0)
            _chunk("fam-a", 0, [1.0, 0.0, 0.0]),
            _chunk("fam-a", 1, [0.0, 1.0, 0.0]),
            # fam-b: (1,0,0) -> score com fam-a = 1/sqrt2
            _chunk("fam-b", 0, [1.0, 0.0, 0.0]),
            # fam-c: (0.6, 0.8, 0) -> score com fam-a = 1.4/sqrt2 = 0.98995
            _chunk("fam-c", 0, [0.6, 0.8, 0.0]),
            # fam-d: ortogonal a fam-a -> score 0
            _chunk("fam-d", 0, [0.0, 0.0, 1.0]),
        ],
    )
    return store


def _client(store: InMemoryVectorStore) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_vector_store] = lambda: store
    return TestClient(app)


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setenv("EMBEDDER", "bedrock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_similar_families_ranks_other_families_by_mean_vector_score(
    real_mode, store: InMemoryVectorStore
) -> None:
    response = _client(store).get("/internal/v1/families/fam-a/similar", params={"top_k": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["family_id"] == "fam-a"
    assert body["model_version"] == REAL_MODEL_VERSION
    similar = body["similar"]
    assert [s["family_id"] for s in similar] == ["fam-c", "fam-b"]
    assert similar[0]["score"] == pytest.approx(1.4 * HALF_SQRT2)
    assert similar[1]["score"] == pytest.approx(HALF_SQRT2)


def test_similar_families_never_returns_the_family_itself(
    real_mode, store: InMemoryVectorStore
) -> None:
    response = _client(store).get("/internal/v1/families/fam-b/similar", params={"top_k": 10})

    ids = [s["family_id"] for s in response.json()["similar"]]
    assert ids == ["fam-a", "fam-c", "fam-d"]


def test_similar_families_defaults_to_top_3(real_mode, store: InMemoryVectorStore) -> None:
    store.index_chunks(INDEX, [_chunk("fam-e", 0, [0.0, 0.6, 0.8])])

    response = _client(store).get("/internal/v1/families/fam-a/similar")

    assert len(response.json()["similar"]) == 3


def test_similar_families_of_unknown_family_is_404(
    real_mode, store: InMemoryVectorStore
) -> None:
    response = _client(store).get("/internal/v1/families/fam-inexistente/similar")

    assert response.status_code == 404


def test_fixture_mode_has_no_vectors_and_returns_no_candidates(
    monkeypatch, store: InMemoryVectorStore
) -> None:
    monkeypatch.setenv("EMBEDDER", "fake")
    get_settings.cache_clear()
    try:
        response = _client(store).get("/internal/v1/families/fam-a/similar")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json() == {"family_id": "fam-a", "model_version": "fixture-demo", "similar": []}
