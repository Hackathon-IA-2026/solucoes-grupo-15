"""Contrato da escolha obrigatoria de escopo de notificacao (TB1 Ticket
8, issue #24, seam 1).

Seam testado: PUT/GET /v1/users/{user_id}/notification-scope - upsert,
leitura, ``null`` quando nao escolhido, 422 em valor invalido. Roda
contra um Postgres real de teste (container Docker, ver
tests/conftest.py), sem precisar popular o catalogo (a preferencia nao
depende de nenhum documento existir).
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


def test_get_scope_is_null_before_any_choice(database_url: str) -> None:
    client = _client(database_url)

    response = client.get("/v1/users/carolina/notification-scope")

    assert response.status_code == 200
    assert response.json() == {"scope": None}


def test_put_scope_persists_and_get_reflects_it(database_url: str) -> None:
    client = _client(database_url)

    put_response = client.put(
        "/v1/users/carolina/notification-scope", json={"scope": "ampla"}
    )
    get_response = client.get("/v1/users/carolina/notification-scope")

    assert put_response.status_code == 200
    assert put_response.json() == {"scope": "ampla"}
    assert get_response.status_code == 200
    assert get_response.json() == {"scope": "ampla"}


def test_put_scope_twice_upserts_instead_of_duplicating(database_url: str) -> None:
    client = _client(database_url)

    client.put("/v1/users/carolina/notification-scope", json={"scope": "estrita"})
    second = client.put("/v1/users/carolina/notification-scope", json={"scope": "ampla"})
    get_response = client.get("/v1/users/carolina/notification-scope")

    assert second.status_code == 200
    assert get_response.json() == {"scope": "ampla"}


def test_put_scope_rejects_invalid_value(database_url: str) -> None:
    client = _client(database_url)

    response = client.put(
        "/v1/users/carolina/notification-scope", json={"scope": "qualquer-coisa"}
    )

    assert response.status_code == 422


def test_scope_is_independent_per_user(database_url: str) -> None:
    client = _client(database_url)

    client.put("/v1/users/carolina/notification-scope", json={"scope": "estrita"})
    client.put("/v1/users/equipe/notification-scope", json={"scope": "ampla"})

    carolina = client.get("/v1/users/carolina/notification-scope")
    equipe = client.get("/v1/users/equipe/notification-scope")

    assert carolina.json() == {"scope": "estrita"}
    assert equipe.json() == {"scope": "ampla"}
