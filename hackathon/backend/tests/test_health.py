"""Contrato do endpoint publico de health check do backend.

Seam testado: GET /v1/health. O backend nunca importa o modulo ai
diretamente - fala com ele so pelo AiClient (cliente HTTP fino). Este
teste substitui o AiClient real por um fake via dependency override do
FastAPI, entao roda em processo, sem Docker e sem rede.
"""

from fastapi.testclient import TestClient

from app.clients.ai_client import get_ai_client
from app.main import create_app


class _FakeAiClient:
    def __init__(self, *, healthy: bool) -> None:
        self._healthy = healthy

    def health(self) -> bool:
        return self._healthy


def _client_with_fake_ai(*, healthy: bool) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeAiClient(healthy=healthy)
    return TestClient(app)


def test_health_reports_ok_when_ai_is_reachable():
    client = _client_with_fake_ai(healthy=True)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"backend": "ok", "ai": "ok"}


def test_health_reports_unreachable_when_ai_call_fails():
    client = _client_with_fake_ai(healthy=False)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"backend": "ok", "ai": "unreachable"}
