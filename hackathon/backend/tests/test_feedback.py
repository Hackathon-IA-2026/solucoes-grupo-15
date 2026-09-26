"""Contrato do endpoint publico de feedback (TB1 Ticket 7, issue #23;
chave de chunk issue #82).

Seam testado: POST /v1/feedback e GET /v1/feedback. Roda contra um
Postgres real de teste (container Docker, ver tests/conftest.py).

Desde a issue #82, a unidade de feedback e o chunk:
``document_version`` + ``chunk_index`` sao obrigatorios no payload;
``family_id`` tornou-se opcional. A tabela ``Feedback`` nao declara
chave estrangeira para nenhuma outra tabela, entao os testes nao
precisam popular o catalogo antes de votar.
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


# ---------------------------------------------------------------------------
# Testes de criacao (POST /v1/feedback)
# ---------------------------------------------------------------------------


def test_create_feedback_with_document_version_and_chunk_index(
    database_url: str,
) -> None:
    """Novo payload primario: document_version + chunk_index, sem family_id."""
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "vote": "up",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-1"
    assert body["document_version"] == "auto-0007-v1"
    assert body["chunk_index"] == 0
    assert body["family_id"] is None
    assert body["vote"] == "up"
    assert isinstance(body["id"], int)
    assert body["created_at"]


def test_create_feedback_with_family_id_optional(database_url: str) -> None:
    """family_id pode ser omitido; document_version e chunk_index sao obrigatorios."""
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "defesa-0007-v2",
            "chunk_index": 3,
            "vote": "down",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["family_id"] is None
    assert body["document_version"] == "defesa-0007-v2"
    assert body["chunk_index"] == 3


def test_create_feedback_with_all_fields_including_family_id(
    database_url: str,
) -> None:
    """family_id pode ser enviado opcionalmente e e persistido."""
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "family_id": "fam-auto-0007",
            "vote": "up",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["family_id"] == "fam-auto-0007"
    assert body["document_version"] == "auto-0007-v1"
    assert body["chunk_index"] == 0


def test_create_feedback_persists_all_fields_and_returns_id_and_created_at(
    database_url: str,
) -> None:
    """Verifica que id e created_at sao gerados automaticamente."""
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 2,
            "family_id": "fam-auto-0007",
            "vote": "up",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-1"
    assert body["document_version"] == "auto-0007-v1"
    assert body["chunk_index"] == 2
    assert body["family_id"] == "fam-auto-0007"
    assert body["vote"] == "up"
    assert isinstance(body["id"], int)
    assert body["created_at"]


def test_create_feedback_rejects_vote_other_than_up_or_down(database_url: str) -> None:
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "vote": "maybe",
        },
    )

    assert response.status_code == 422


def test_create_feedback_rejects_missing_document_version(database_url: str) -> None:
    """document_version e obrigatorio — omitir deve retornar 422."""
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "chunk_index": 0, "vote": "up"},
    )

    assert response.status_code == 422


def test_create_feedback_rejects_missing_chunk_index(database_url: str) -> None:
    """chunk_index e obrigatorio — omitir deve retornar 422."""
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={"request_id": "req-1", "document_version": "auto-0007-v1", "vote": "up"},
    )

    assert response.status_code == 422


def test_create_feedback_does_not_require_a_family_id_field(database_url: str) -> None:
    """family_id e opcional — omitir nao causa erro."""
    client = _client(database_url)

    response = client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "vote": "down",
        },
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Testes de listagem (GET /v1/feedback)
# ---------------------------------------------------------------------------


def test_list_feedback_returns_what_was_created(database_url: str) -> None:
    client = _client(database_url)
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "vote": "up",
        },
    )
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-2",
            "document_version": "defesa-0007-v2",
            "chunk_index": 1,
            "vote": "down",
        },
    )

    response = client.get("/v1/feedback")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    keys = {
        (item["request_id"], item["document_version"], item["chunk_index"], item["vote"])
        for item in body
    }
    assert keys == {
        ("req-1", "auto-0007-v1", 0, "up"),
        ("req-2", "defesa-0007-v2", 1, "down"),
    }


def test_list_feedback_filters_by_request_id(database_url: str) -> None:
    client = _client(database_url)
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "vote": "up",
        },
    )
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-2",
            "document_version": "defesa-0007-v2",
            "chunk_index": 1,
            "vote": "down",
        },
    )

    response = client.get("/v1/feedback", params={"request_id": "req-1"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["request_id"] == "req-1"


def test_list_feedback_filters_by_document_version(database_url: str) -> None:
    client = _client(database_url)
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "vote": "up",
        },
    )
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-2",
            "document_version": "defesa-0007-v2",
            "chunk_index": 1,
            "vote": "down",
        },
    )

    response = client.get(
        "/v1/feedback", params={"document_version": "defesa-0007-v2"}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["document_version"] == "defesa-0007-v2"


def test_list_feedback_filters_by_chunk_index(database_url: str) -> None:
    client = _client(database_url)
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "vote": "up",
        },
    )
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-2",
            "document_version": "auto-0007-v1",
            "chunk_index": 5,
            "vote": "down",
        },
    )

    response = client.get("/v1/feedback", params={"chunk_index": 5})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["chunk_index"] == 5


def test_list_feedback_filters_by_family_id(database_url: str) -> None:
    """family_id ainda funciona como filtro (campo opcional, mas preservado)."""
    client = _client(database_url)
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-1",
            "document_version": "auto-0007-v1",
            "chunk_index": 0,
            "family_id": "fam-auto-0007",
            "vote": "up",
        },
    )
    client.post(
        "/v1/feedback",
        json={
            "request_id": "req-2",
            "document_version": "defesa-0007-v2",
            "chunk_index": 1,
            "family_id": "fam-defesa-0007",
            "vote": "down",
        },
    )

    response = client.get("/v1/feedback", params={"family_id": "fam-defesa-0007"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["family_id"] == "fam-defesa-0007"
