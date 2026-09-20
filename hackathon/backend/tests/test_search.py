"""Contrato do endpoint publico de busca (TB1 Ticket 3, issue #19).

Seam testado: POST /v1/search. Isola o ai via dependency override de
get_ai_client (fake deterministico com hits crus fixos - nunca chama o
ai real por HTTP) e roda contra um Postgres real de teste (container
Docker, ver tests/conftest.py), populado via ``run_ingestion``
(reaproveitada da issue #18) antes de cada teste, para que os IDs
usados nos hits fake existam no catalogo.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import (
    AiSearchHit,
    AiSearchResponse,
    IndexDocumentPayload,
    IndexReport,
    get_ai_client,
)
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.fixtures.loader import load_demo_corpus
from app.main import create_app
from app.routes.ingestions import run_ingestion


class _SeedAiClient:
    """Fake deterministico usado so para popular o catalogo via
    run_ingestion antes de cada teste (mesmo padrao de test_ingestions.py).
    """

    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        return [
            IndexReport(
                document_version=doc.document_version,
                extracted_text_locator=f"/data/documents/{doc.document_version}/extracted.txt",
                chunks_indexed=1,
                model_version="fixture-demo",
            )
            for doc in documents
        ]


class _FakeSearchAiClient:
    """Fake deterministico de AiClient.search - devolve hits crus fixos,
    nunca chama o ai real por HTTP.
    """

    def __init__(self, hits: list[AiSearchHit]) -> None:
        self._hits = hits

    def search(self, query: str, top_k: int | None = None) -> AiSearchResponse:
        hits = self._hits if top_k is None else self._hits[:top_k]
        return AiSearchResponse(hits=hits, model_version="fixture-demo")


def _client(database_url: str, hits: list[AiSearchHit]) -> TestClient:
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)

    def _override_session():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    _seed_catalog(session_factory)

    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeSearchAiClient(hits)
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app)


def _seed_catalog(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        run_ingestion(load_demo_corpus(), ai_client=_SeedAiClient(), session=session)
        session.commit()


def test_search_groups_hits_from_two_versions_of_same_family_into_one_result(
    database_url: str,
) -> None:
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho na versao antiga",
            score=0.7,
        ),
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v2",
            excerpt="trecho na versao nova",
            score=0.9,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    result = results[0]
    assert result["family_id"] == "fam-auto-0007"
    assert [c["document_version"] for c in result["matched_chunks"]] == [
        "docver-auto-0007-v1",
        "docver-auto-0007-v2",
    ]


def test_search_face_is_latest_version_even_when_matched_chunk_is_older(
    database_url: str,
) -> None:
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho na versao antiga",
            score=0.5,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    result = response.json()["results"][0]
    assert result["face"]["document_version"] == "docver-auto-0007-v2"
    assert result["face"]["version_date"] == "2024-04-18"
    [chunk] = result["matched_chunks"]
    assert chunk["document_version"] == "docver-auto-0007-v1"
    assert chunk["is_latest"] is False


def test_search_marks_is_latest_true_only_for_the_face_version(database_url: str) -> None:
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho antigo",
            score=0.6,
        ),
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v2",
            excerpt="trecho novo",
            score=0.95,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    [result] = response.json()["results"]
    is_latest_by_version = {c["document_version"]: c["is_latest"] for c in result["matched_chunks"]}
    assert is_latest_by_version == {
        "docver-auto-0007-v1": False,
        "docver-auto-0007-v2": True,
    }


def test_search_never_repeats_the_same_family_and_preserves_first_occurrence_order(
    database_url: str,
) -> None:
    hits = [
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="trecho defesa",
            score=0.3,
        ),
        AiSearchHit(
            family_id="fam-decisao-0007",
            document_version="docver-decisao-0007-v1",
            excerpt="trecho decisao",
            score=0.95,
        ),
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="segundo trecho defesa",
            score=0.4,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    results = response.json()["results"]
    family_ids = [r["family_id"] for r in results]
    assert family_ids == ["fam-defesa-0007", "fam-decisao-0007"]
    assert len(family_ids) == len(set(family_ids))
    # score mais alto (fam-decisao-0007) NAO e promovido para primeiro -
    # a ordem e a de primeira ocorrencia devolvida pelo ai, nunca por score.
    assert family_ids[0] == "fam-defesa-0007"


def test_search_envelope_has_all_required_fields(database_url: str) -> None:
    hits = [
        AiSearchHit(
            family_id="fam-norma-1000",
            document_version="docver-norma-1000-v1",
            excerpt="trecho norma",
            score=0.8,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "demo"
    assert body["corpus_version"] == "demo-v1"
    assert body["model_version"] == "fixture-demo"
    assert body["ranking_version"] == "demo-ranking-v1"
    assert uuid.UUID(body["request_id"])


def test_search_request_id_is_unique_per_call(database_url: str) -> None:
    client = _client(database_url, hits=[])

    first = client.post("/v1/search", json={"query": "qualquer consulta"}).json()
    second = client.post("/v1/search", json={"query": "qualquer consulta"}).json()

    assert first["request_id"] != second["request_id"]


def test_search_returns_empty_results_and_full_envelope_when_ai_returns_no_hits(
    database_url: str,
) -> None:
    client = _client(database_url, hits=[])

    response = client.post("/v1/search", json={"query": "consulta sem correspondencia"})

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["data_mode"] == "demo"
    assert body["model_version"] == "fixture-demo"
    assert body["ranking_version"] == "demo-ranking-v1"
    # Sem nenhuma familia da qual derivar: cai para o fallback de settings
    # (Settings.default_corpus_version), que hoje coincide com o
    # corpus_version do corpus fixture ("demo-v1").
    assert body["corpus_version"] == "demo-v1"
    assert uuid.UUID(body["request_id"])
