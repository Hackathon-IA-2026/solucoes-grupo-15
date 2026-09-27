"""Contrato de ``AUTH_MODE=none|cognito`` (issue #104, parent #101).

Seam testado: a seam HTTP do backend (``create_app`` + ``TestClient``).
As chaves RSA sao geradas aqui mesmo e o verificador de token
(``get_token_verifier``) e injetado por ``dependency_overrides`` com a
chave publica do teste no lugar do JWKS do User Pool - sem rede e sem
AWS. Os tokens seguem o formato do access token do Cognito: ``iss`` do
pool, ``client_id``, ``token_use``, ``exp``, ``username`` e
``cognito:groups``.
"""

import json
import time
from collections.abc import Iterator

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import CognitoTokenVerifier, get_token_verifier
from app.clients.ai_client import get_ai_client
from app.config import get_settings
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.main import create_app
from tests.test_notifications_api import _FakeAiClient as _IndexingAiClient

_REGION = "us-east-1"
_POOL_ID = "us-east-1_TESTPOOL"
_CLIENT_ID = "client-capiwatt-teste"
_ISSUER = f"https://cognito-idp.{_REGION}.amazonaws.com/{_POOL_ID}"
_KID = "kid-teste"

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeAiClient:
    def health(self) -> bool:
        return True


@pytest.fixture
def cognito_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AUTH_MODE", "cognito")
    monkeypatch.setenv("COGNITO_REGION", _REGION)
    monkeypatch.setenv("COGNITO_USER_POOL_ID", _POOL_ID)
    monkeypatch.setenv("COGNITO_CLIENT_ID", _CLIENT_ID)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _test_verifier() -> CognitoTokenVerifier:
    public_key = _PRIVATE_KEY.public_key()

    def _signing_key(kid: str):
        assert kid == _KID
        return public_key

    return CognitoTokenVerifier(issuer=_ISSUER, client_id=_CLIENT_ID, signing_key=_signing_key)


def _app():
    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeAiClient()
    app.dependency_overrides[get_token_verifier] = _test_verifier
    return app


def _db_app(database_url: str):
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

    app = _app()
    app.dependency_overrides[get_ai_client] = lambda: _IndexingAiClient()
    app.dependency_overrides[get_db_session] = _override_session
    return app


def _token(
    username: str = "carolina",
    *,
    groups: list[str] | None = None,
    client_id: str = _CLIENT_ID,
    token_use: str = "access",
    expires_in: int = 3600,
    key=None,
) -> str:
    now = int(time.time())
    claims = {
        "iss": _ISSUER,
        "sub": f"sub-{username}",
        "username": username,
        "client_id": client_id,
        "token_use": token_use,
        "iat": now,
        "exp": now + expires_in,
    }
    if groups is not None:
        claims["cognito:groups"] = groups
    return jwt.encode(claims, key or _PRIVATE_KEY, algorithm="RS256", headers={"kid": _KID})


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_cognito_request_without_token_is_401(cognito_env):
    client = TestClient(_app())

    response = client.get("/v1/users/carolina/notification-scope")

    assert response.status_code == 401


def test_cognito_valid_token_reaches_the_route_and_logs_the_username(
    cognito_env, database_url, capsys
):
    client = TestClient(_db_app(database_url))
    capsys.readouterr()

    response = client.get("/v1/users/carolina/notification-scope", headers=_auth(_token()))

    assert response.status_code == 200
    assert response.json() == {"scope": None}
    [line] = [json.loads(raw) for raw in capsys.readouterr().out.splitlines() if raw.strip()]
    assert line["user_id"] == "carolina"


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(_token(expires_in=-60), id="expirado"),
        pytest.param(_token(client_id="outro-client"), id="outro-client_id"),
        pytest.param(_token(token_use="id"), id="token_use-id"),
        pytest.param(_token(key=_OTHER_PRIVATE_KEY), id="assinatura-invalida"),
        pytest.param("nao-e-um-jwt", id="malformado"),
    ],
)
def test_cognito_invalid_token_is_401(cognito_env, token):
    client = TestClient(_app())

    response = client.get("/v1/users/carolina/notification-scope", headers=_auth(token))

    assert response.status_code == 401


def test_cognito_health_answers_200_without_token(cognito_env):
    client = TestClient(_app())

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"backend": "ok", "ai": "ok"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/v1/users/equipe/notifications"),
        ("GET", "/v1/users/equipe/notification-scope"),
        ("PUT", "/v1/users/equipe/notification-scope"),
        ("GET", "/v1/users/equipe/email-digests"),
    ],
)
def test_cognito_user_path_diverging_from_token_is_403(cognito_env, method, path):
    client = TestClient(_app())

    response = client.request(
        method, path, headers=_auth(_token("carolina")), json={"scope": "estrita"}
    )

    assert response.status_code == 403


@pytest.mark.parametrize("path", ["/v1/ingestions", "/v1/demo/reset"])
@pytest.mark.parametrize("groups", [None, [], ["leitores"]])
def test_cognito_admin_routes_without_admin_group_are_403(cognito_env, path, groups):
    client = TestClient(_app())

    response = client.post(path, headers=_auth(_token("carolina", groups=groups)))

    assert response.status_code == 403


def test_cognito_admin_routes_succeed_with_admin_group(cognito_env, database_url):
    client = TestClient(_db_app(database_url))
    admin = _auth(_token("admin", groups=["admin"]))

    ingestion = client.post("/v1/ingestions", headers=admin)
    reset = client.post("/v1/demo/reset", headers=admin)

    assert ingestion.status_code == 200
    assert ingestion.json()["versions_count"] > 0
    assert reset.status_code == 200


def test_cognito_notification_opened_event_records_the_token_user_id(cognito_env, database_url):
    client = TestClient(_db_app(database_url))
    carolina = _auth(_token("carolina"))
    client.put("/v1/users/carolina/notification-scope", json={"scope": "estrita"}, headers=carolina)
    client.post("/v1/ingestions", headers=_auth(_token("admin", groups=["admin"])))
    [first, *_] = client.get("/v1/users/carolina/notifications", headers=carolina).json()

    opened = client.post(f"/v1/notifications/{first['id']}/opened", headers=_auth(_token("equipe")))

    assert opened.status_code == 200
    events = client.get(
        "/v1/notification-events", params={"user_id": "equipe"}, headers=carolina
    ).json()
    assert [(e["event_type"], e["notification_id"]) for e in events] == [
        ("notification_opened", first["id"])
    ]


@pytest.mark.parametrize("missing", ["COGNITO_REGION", "COGNITO_USER_POOL_ID", "COGNITO_CLIENT_ID"])
def test_cognito_without_pool_config_refuses_to_start_with_clear_message(
    cognito_env, monkeypatch, missing
):
    monkeypatch.delenv(missing)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match=f"AUTH_MODE=cognito exige {missing}"):
        create_app()


def test_unknown_auth_mode_refuses_to_start(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "cognto")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="AUTH_MODE='cognto' invalido"):
            create_app()
    finally:
        get_settings.cache_clear()


def test_none_mode_is_the_default_and_requires_no_header(monkeypatch, database_url):
    monkeypatch.delenv("AUTH_MODE", raising=False)
    get_settings.cache_clear()
    client = TestClient(_db_app(database_url))

    scope = client.put("/v1/users/carolina/notification-scope", json={"scope": "ampla"})
    other = client.get("/v1/users/equipe/notifications")
    ingestion = client.post("/v1/ingestions")
    reset = client.post("/v1/demo/reset")

    assert scope.status_code == 200
    assert other.status_code == 200
    assert ingestion.status_code == 200
    assert reset.status_code == 200
