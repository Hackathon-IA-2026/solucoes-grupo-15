"""Contrato da linha de log JSON por requisicao (issue #103, parent #101).

Seam testado: a seam HTTP do backend (``create_app`` + ``TestClient`` com
``dependency_overrides``), capturando o stdout do processo (``capsys``).
Toda requisicao a ``/v1/*`` escreve exatamente uma linha JSON com os oito
campos decididos em topic-aws-observability (#99), no mesmo formato no
Compose e na AWS.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.clients.ai_client import AiSearchHit, get_ai_client
from app.main import create_app
from tests.test_search import _client as _search_client

_FIELDS = {
    "ts",
    "method",
    "path",
    "status",
    "duration_ms",
    "user_id",
    "trace_id",
    "search_request_id",
}


class _FakeAiClient:
    def health(self) -> bool:
        return True


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeAiClient()
    return TestClient(app)


def _log_lines(capsys: pytest.CaptureFixture[str]) -> list[dict]:
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def test_health_request_writes_exactly_one_json_line_with_the_eight_fields(capsys):
    client = _client()
    capsys.readouterr()

    response = client.get("/v1/health")

    assert response.status_code == 200
    lines = _log_lines(capsys)
    assert len(lines) == 1
    line = lines[0]
    assert set(line) == _FIELDS
    assert line["method"] == "GET"
    assert line["path"] == "/v1/health"
    assert line["status"] == 200
    assert isinstance(line["duration_ms"], int | float)
    assert line["duration_ms"] >= 0
    assert isinstance(line["ts"], str) and line["ts"]
    assert line["user_id"] == "-"
    assert line["trace_id"] == "-"
    assert line["search_request_id"] == "-"


def test_trace_id_is_the_alb_header_when_present(capsys):
    client = _client()
    capsys.readouterr()
    trace = "Root=1-67891233-abcdef012345678912345678"

    client.get("/v1/health", headers={"X-Amzn-Trace-Id": trace})

    [line] = _log_lines(capsys)
    assert line["trace_id"] == trace


class _BrokenAiClient:
    def health(self) -> bool:
        raise RuntimeError("falha inesperada")


def test_unhandled_error_writes_the_line_with_status_500(capsys):
    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _BrokenAiClient()
    client = TestClient(app, raise_server_exceptions=False)
    capsys.readouterr()

    response = client.get("/v1/health")

    assert response.status_code == 500
    [line] = _log_lines(capsys)
    assert line["status"] == 500
    assert line["path"] == "/v1/health"


def test_client_error_writes_the_line_with_the_4xx_status(capsys):
    client = _client()
    capsys.readouterr()

    response = client.get("/v1/rota-que-nao-existe")

    assert response.status_code == 404
    [line] = _log_lines(capsys)
    assert line["status"] == 404
    assert line["search_request_id"] == "-"


_QUERY_MARKER = "consulta-marcador-9f3c"
_TOKEN_MARKER = "token-marcador-7b1e"


def test_search_line_carries_the_envelope_request_id_and_no_secret(database_url, capsys):
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho casado",
            score=0.7,
        ),
    ]
    client = _search_client(database_url, hits)
    capsys.readouterr()

    response = client.post(
        "/v1/search",
        json={"query": _QUERY_MARKER},
        headers={"Authorization": f"Bearer {_TOKEN_MARKER}"},
    )

    assert response.status_code == 200
    out = capsys.readouterr().out
    [line] = [json.loads(raw) for raw in out.splitlines() if raw.strip()]
    assert line["method"] == "POST"
    assert line["path"] == "/v1/search"
    assert line["search_request_id"] == response.json()["request_id"]
    assert _QUERY_MARKER not in out
    assert _TOKEN_MARKER not in out
    assert "Bearer" not in out


def test_search_validation_error_writes_the_line_with_status_422(database_url, capsys):
    client = _search_client(database_url, [])
    capsys.readouterr()

    response = client.post("/v1/search", json={"limit": 3})

    assert response.status_code == 422
    [line] = _log_lines(capsys)
    assert line["status"] == 422
    assert line["search_request_id"] == "-"


def test_search_cursor_continuation_line_carries_the_original_request_id(database_url, capsys):
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt=f"trecho {i}",
            score=0.9 - i / 10,
        )
        for i in range(3)
    ]
    client = _search_client(database_url, hits)
    first = client.post("/v1/search", json={"query": "q", "limit": 2}).json()
    capsys.readouterr()

    response = client.post(
        "/v1/search", json={"query": "q", "limit": 2, "cursor": first["next_cursor"]}
    )

    assert response.status_code == 200
    [line] = _log_lines(capsys)
    assert line["search_request_id"] == first["request_id"]


def test_user_id_comes_from_the_request_identity_when_an_auth_layer_sets_it(capsys):
    # Simula o futuro modulo de auth (#104, AUTH_MODE=cognito): uma camada
    # externa que grava a identidade em request.state.user_id.
    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeAiClient()

    @app.middleware("http")
    async def _fake_auth(request, call_next):
        request.state.user_id = "carolina"
        return await call_next(request)

    client = TestClient(app)
    capsys.readouterr()

    client.get("/v1/health")

    [line] = _log_lines(capsys)
    assert line["user_id"] == "carolina"
