"""Contrato do reset de interacoes da demonstracao (issue #38)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import IndexDocumentPayload, IndexReport, get_ai_client
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.main import create_app
from app.models import (
    DocumentFamily,
    DocumentRelation,
    DocumentVersion,
    Feedback,
    SearchExecution,
)


class _FakeAiClient:
    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        return [
            IndexReport(
                document_version=document.document_version,
                extracted_text_locator=f"/data/documents/{document.document_version}/extracted.txt",
                chunks_indexed=1,
                model_version="fixture-demo",
            )
            for document in documents
        ]


def _client(database_url: str) -> tuple[TestClient, sessionmaker[Session]]:
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

    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeAiClient()
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app), session_factory


def test_reset_clears_interactions_and_preserves_document_corpus(database_url: str) -> None:
    client, session_factory = _client(database_url)
    client.put("/v1/users/carolina/notification-scope", json={"scope": "ampla"})
    client.post("/v1/ingestions")

    with session_factory() as session:
        session.add(Feedback(request_id="request-1", family_id="fam-auto-0007", vote="up"))
        session.add(
            SearchExecution(
                request_id="request-1",
                query="consulta demo",
                data_mode="demo",
                corpus_version="demo-v1",
                model_version="fixture-demo",
                ranking_version="demo-ranking-v1",
                raw_hits_json="[]",
                response_json="{}",
                code_reference="test",
            )
        )
        before = _corpus_counts(session)
        session.commit()

    response = client.post("/v1/demo/reset")

    assert response.status_code == 200
    deleted = response.json()["deleted"]
    assert deleted["notification_scope_preferences"] == 1
    assert deleted["notifications"] == 5
    assert deleted["email_digests"] == 1
    assert deleted["feedback"] == 1
    assert deleted["search_executions"] == 1
    assert deleted["notification_events"] > 0
    assert client.get("/v1/users/carolina/notification-scope").json() == {"scope": None}
    assert client.get("/v1/users/carolina/notifications").json() == []
    assert client.get("/v1/feedback").json() == []

    with session_factory() as session:
        assert _corpus_counts(session) == before


def test_reset_is_idempotent(database_url: str) -> None:
    client, _ = _client(database_url)

    first = client.post("/v1/demo/reset")
    second = client.post("/v1/demo/reset")

    assert first.status_code == 200
    assert second.status_code == 200
    assert all(count == 0 for count in second.json()["deleted"].values())


def _corpus_counts(session: Session) -> tuple[int, int, int]:
    return (
        session.scalar(select(func.count()).select_from(DocumentFamily)) or 0,
        session.scalar(select(func.count()).select_from(DocumentVersion)) or 0,
        session.scalar(select(func.count()).select_from(DocumentRelation)) or 0,
    )
