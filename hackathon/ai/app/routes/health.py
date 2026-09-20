"""Rota de health check interno do modulo ai.

Faz parte da superficie HTTP /internal/v1/*, consumida apenas pelo
backend (nunca pelo frontend). Neste ticket nao verifica dependencias
reais (OpenSearch, embedder) - so confirma que o processo do ai esta
de pe, servindo de seam para o health check cruzado do backend.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/internal/v1", tags=["internal"])


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}
