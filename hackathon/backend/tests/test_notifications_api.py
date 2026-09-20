"""Contrato de leitura de notificacoes + eventos de abertura (TB1
Ticket 8, issue #24).

Seams testados: GET /v1/users/{user_id}/notifications (enriquecido com
document_type/document_id do catalogo), POST
/v1/notifications/{notification_id}/opened (registra
notification_opened), GET /v1/notification-events (filtros por
user_id/document_version_id) e GET /v1/users/{user_id}/email-digests.
Popula notificacoes via POST /v1/ingestions (mesmo fluxo real), roda
contra um Postgres real de teste (container Docker, ver
tests/conftest.py).
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import IndexDocumentPayload, IndexReport, get_ai_client
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.main import create_app


class _FakeAiClient:
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


def _seed_carolina_with_notifications(client: TestClient) -> None:
    client.put("/v1/users/carolina/notification-scope", json={"scope": "estrita"})
    client.post("/v1/ingestions")


def test_list_notifications_returns_most_recent_first_enriched_with_catalog(
    database_url: str,
) -> None:
    client, _ = _client(database_url)
    _seed_carolina_with_notifications(client)

    response = client.get("/v1/users/carolina/notifications")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    # mais recente primeiro -> ids em ordem decrescente.
    ids = [item["id"] for item in body]
    assert ids == sorted(ids, reverse=True)
    for item in body:
        assert item["document_type"]
        assert item["document_id"]
        assert item["family_id"]
        assert item["scope_effective"] == "estrita"
        assert item["reasons"] == [{"type": "novo_documento"}]


def test_list_notifications_empty_for_user_without_notifications(database_url: str) -> None:
    client, _ = _client(database_url)

    response = client.get("/v1/users/ninguem/notifications")

    assert response.status_code == 200
    assert response.json() == []


def test_mark_notification_opened_records_event(database_url: str) -> None:
    client, session_factory = _client(database_url)
    _seed_carolina_with_notifications(client)
    notifications = client.get("/v1/users/carolina/notifications").json()
    notification_id = notifications[0]["id"]

    response = client.post(f"/v1/notifications/{notification_id}/opened")

    assert response.status_code == 200
    assert response.json() == {"notification_id": notification_id, "opened": True}

    events = client.get(
        "/v1/notification-events", params={"user_id": "carolina"}
    ).json()
    opened_events = [e for e in events if e["event_type"] == "notification_opened"]
    assert len(opened_events) == 1
    assert opened_events[0]["notification_id"] == notification_id
    assert opened_events[0]["payload"] == {"origin": "home"}


def test_mark_notification_opened_404_for_unknown_id(database_url: str) -> None:
    client, _ = _client(database_url)

    response = client.post("/v1/notifications/999999/opened")

    assert response.status_code == 404


def test_notification_events_filter_by_document_version_id(database_url: str) -> None:
    client, _ = _client(database_url)
    _seed_carolina_with_notifications(client)

    response = client.get(
        "/v1/notification-events",
        params={"document_version_id": "docver-auto-0007-v1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(e["document_version_id"] == "docver-auto-0007-v1" for e in body)


def test_notification_events_auditable_no_duplicate_generated_per_user_and_version(
    database_url: str,
) -> None:
    client, _ = _client(database_url)
    _seed_carolina_with_notifications(client)
    client.post("/v1/ingestions")  # reingestao - nao deve duplicar notification_generated.

    events = client.get(
        "/v1/notification-events",
        params={"user_id": "carolina"},
    ).json()
    generated = [e for e in events if e["event_type"] == "notification_generated"]

    seen: set[str] = set()
    for event in generated:
        key = event["document_version_id"]
        assert key not in seen
        seen.add(key)


def test_list_email_digests_returns_rendered_preview(database_url: str) -> None:
    client, _ = _client(database_url)
    _seed_carolina_with_notifications(client)

    response = client.get("/v1/users/carolina/email-digests")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == "carolina"
    assert body[0]["rendered_body"].strip() != ""
    assert len(body[0]["notification_ids"]) == 5


def test_list_email_digests_empty_for_user_without_digests(database_url: str) -> None:
    client, _ = _client(database_url)

    response = client.get("/v1/users/ninguem/email-digests")

    assert response.status_code == 200
    assert response.json() == []
