"""Contrato do endpoint de health check interno do modulo ai.

Seam testado: GET /internal/v1/health, chamado pelo backend via HTTP
(nunca importando o modulo ai diretamente). Nao depende de Docker nem
de rede: roda direto contra o app FastAPI em processo.
"""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok_status():
    client = TestClient(create_app())

    response = client.get("/internal/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
