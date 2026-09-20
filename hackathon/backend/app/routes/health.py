"""Rota publica de health check cruzado do backend.

GET /v1/health verifica o proprio backend e, transitivamente, o ai
(via AiClient.health(), que fala HTTP com /internal/v1/health -
nunca importa o modulo ai). Se o ai nao responder, o backend continua
respondendo 200 com "ai": "unreachable" em vez de propagar o erro.
"""

from fastapi import APIRouter, Depends

from app.clients.ai_client import AiClient, get_ai_client

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
def get_health(ai_client: AiClient = Depends(get_ai_client)) -> dict[str, str]:
    ai_status = "ok" if ai_client.health() else "unreachable"
    return {"backend": "ok", "ai": ai_status}
