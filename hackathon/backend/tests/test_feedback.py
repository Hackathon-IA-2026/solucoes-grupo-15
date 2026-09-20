"""Contrato do endpoint publico de feedback (TB1 Ticket 7, issue #23).

Seam testado: POST /v1/feedback e GET /v1/feedback. Roda contra um
Postgres real de teste (container Docker, ver tests/conftest.py) -
``Feedback`` nao declara chave estrangeira para ``document_family``
(ver models.py), entao os testes nao precisam popular o catalogo antes
de votar.
"""

from fastapi.testclient import TestClient

from app.db import Base, get_db_session, make_engine, make_session_factory
from app.main import create_app


def _client(database_url: str) -> TestClient:
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
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app)


def test_create_feedback_persists_the_three_fields_and_returns_id_and_created_at(
    database_url: str,
) -> None:
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "family_id": "fam-auto-0007", "vote": "up"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-1"
    assert body["family_id"] == "fam-auto-0007"
    assert body["vote"] == "up"
    assert isinstance(body["id"], int)
    assert body["created_at"]


def test_create_feedback_rejects_vote_other_than_up_or_down(database_url: str) -> None:
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "family_id": "fam-auto-0007", "vote": "maybe"},
    )

    assert response.status_code == 422


def test_create_feedback_does_not_require_a_comment_field(database_url: str) -> None:
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "family_id": "fam-auto-0007", "vote": "down"},
    )

    assert response.status_code == 200


def test_list_feedback_returns_what_was_created(database_url: str) -> None:
    client = _client(database_url)
    client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "family_id": "fam-auto-0007", "vote": "up"},
    )
    client.post(
        "/v1/feedback",
        json={"request_id": "req-2", "family_id": "fam-defesa-0007", "vote": "down"},
    )

    response = client.get("/v1/feedback")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    votes = {(item["request_id"], item["family_id"], item["vote"]) for item in body}
    assert votes == {
        ("req-1", "fam-auto-0007", "up"),
        ("req-2", "fam-defesa-0007", "down"),
    }


def test_list_feedback_filters_by_request_id(database_url: str) -> None:
    client = _client(database_url)
    client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "family_id": "fam-auto-0007", "vote": "up"},
    )
    client.post(
        "/v1/feedback",
        json={"request_id": "req-2", "family_id": "fam-defesa-0007", "vote": "down"},
    )

    response = client.get("/v1/feedback", params={"request_id": "req-1"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["request_id"] == "req-1"


def test_list_feedback_filters_by_family_id(database_url: str) -> None:
    client = _client(database_url)
    client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "family_id": "fam-auto-0007", "vote": "up"},
    )
    client.post(
        "/v1/feedback",
        json={"request_id": "req-2", "family_id": "fam-defesa-0007", "vote": "down"},
    )

    response = client.get("/v1/feedback", params={"family_id": "fam-defesa-0007"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["family_id"] == "fam-defesa-0007"
