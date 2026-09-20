"""Cliente HTTP fino para o modulo ai.

Invariante de arquitetura (vale desde o Ticket 1): o backend nunca
importa o modulo ai diretamente, so fala com ele por HTTP contra
/internal/v1/*. Este cliente sera expandido em tickets futuros com os
demais nomes de operacao do port VectorService (index, search,
similar_families, reassign_family, delete/reindex); por ora so cobre o
health check interno.
"""

import httpx

from app.config import get_settings


class AiClient:
    """Cliente tipado a partir dos nomes de operacao do port VectorService."""

    def __init__(self, base_url: str, timeout: float = 2.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def health(self) -> bool:
        """Consulta GET /internal/v1/health no ai.

        Devolve True se o ai respondeu 200 com status "ok"; False para
        qualquer falha de rede, timeout ou resposta inesperada (nunca
        propaga a excecao para quem chamou).
        """
        try:
            response = httpx.get(f"{self._base_url}/internal/v1/health", timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError:
            return False
        return response.json().get("status") == "ok"


def get_ai_client() -> AiClient:
    settings = get_settings()
    return AiClient(base_url=settings.ai_base_url)
