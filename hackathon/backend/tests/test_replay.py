"""Contrato de replay deterministico de busca (TB1 Ticket 9, issue #25).

Seam testado: ``replay_search(request_id, session)``. Popula o catalogo
via ``run_ingestion`` (reaproveitada da issue #18), roda uma busca real
via ``TestClient`` (com um fake de ``AiClient``, so para gravar
``SearchExecution`` - ver test_search.py) e entao chama
``replay_search`` passando SO a ``session``. Nenhum ``AiClient``/fake
de ``AiClient`` existe neste modulo de teste alem do necessario para
GRAVAR a execucao original - a chamada a ``replay_search`` em si nunca
recebe nem tem como receber um cliente ai (a assinatura da funcao so
aceita ``request_id``/``session``), o que prova estruturalmente que o
replay nao depende de rede nem do servico ai.
"""

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
from app.replay import SearchExecutionNotFound, replay_search
from app.routes.ingestions import run_ingestion


class _SeedAiClient:
    """Fake deterministico usado so para popular o catalogo via
    run_ingestion antes de cada teste (mesmo padrao de test_search.py).
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
    """Fake deterministico de AiClient.search, usado so para gravar a
    execucao original via POST /v1/search - nunca passado para
    replay_search (ver docstring do modulo).
    """

    def __init__(self, hits: list[AiSearchHit]) -> None:
        self._hits = hits

    def search(self, query: str, top_k: int | None = None) -> AiSearchResponse:
        hits = self._hits if top_k is None else self._hits[:top_k]
        return AiSearchResponse(hits=hits, model_version="fixture-demo")


def _seed_catalog(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        run_ingestion(load_demo_corpus(), ai_client=_SeedAiClient(), session=session)
        session.commit()


def _record_a_search(
    database_url: str, hits: list[AiSearchHit], query: str = "qualquer consulta"
) -> tuple[str, sessionmaker[Session]]:
    """Sobe um app real (com fake de AiClient) so para produzir uma
    SearchExecution gravada, e devolve o request_id + a session_factory
    do mesmo Postgres de teste - para que o teste possa depois chamar
    replay_search sem nenhum app/fake de AiClient no meio.
    """
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
    client = TestClient(app)

    response = client.post("/v1/search", json={"query": query})
    request_id = response.json()["request_id"]
    return request_id, session_factory


def test_replay_search_recomputes_the_same_results_in_the_same_order(
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
    request_id, session_factory = _record_a_search(database_url, hits)

    with session_factory() as session:
        result = replay_search(request_id, session)

    assert result.request_id == request_id
    assert result.matches is True
    assert result.recomputed_response == result.original_response
    [recomputed_result] = result.recomputed_response.results
    assert recomputed_result.family_id == "fam-auto-0007"
    assert [c.document_version for c in recomputed_result.matched_chunks] == [
        "docver-auto-0007-v1",
        "docver-auto-0007-v2",
    ]


def test_replay_search_preserves_family_order_across_multiple_families(
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
    ]
    request_id, session_factory = _record_a_search(database_url, hits)

    with session_factory() as session:
        result = replay_search(request_id, session)

    assert result.matches is True
    assert [r.family_id for r in result.recomputed_response.results] == [
        "fam-defesa-0007",
        "fam-decisao-0007",
    ]


def test_replay_search_raises_a_clear_error_for_an_unknown_request_id(
    database_url: str,
) -> None:
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        try:
            replay_search("does-not-exist", session)
        except SearchExecutionNotFound as exc:
            assert "does-not-exist" in str(exc)
        else:
            raise AssertionError("deveria ter levantado SearchExecutionNotFound")
