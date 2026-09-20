"""Cliente HTTP fino para o modulo ai.

Invariante de arquitetura (vale desde o Ticket 1): o backend nunca
importa o modulo ai diretamente, so fala com ele por HTTP contra
/internal/v1/*. Ticket 2 adiciona ``index`` (contrato do port
VectorService, issue #16); as demais operacoes (search,
similar_families, reassign_family, delete/reindex) ficam para tickets
futuros.
"""

from dataclasses import dataclass

import httpx
from pydantic import BaseModel

from app.config import get_settings


@dataclass(frozen=True)
class IndexDocumentPayload:
    """Um documento a indexar: document_version + texto ja pronto.

    Metadados de catalogo (family_id, datas, processo_numero) nao
    fazem parte deste payload - o ``ai`` so processa texto/versao; o
    catalogo e responsabilidade exclusiva do backend.
    """

    document_version: str
    text: str


class IndexReport(BaseModel):
    """Espelha o IndexReport devolvido por POST /internal/v1/index."""

    document_version: str
    extracted_text_locator: str
    chunks_indexed: int
    model_version: str


class AiClient:
    """Cliente tipado a partir dos nomes de operacao do port VectorService."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
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

    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        """Chama POST /internal/v1/index no ai e devolve os IndexReports.

        Ao contrario de ``health``, propaga erros HTTP/rede - quem
        ingere (POST /v1/ingestions) precisa saber se a indexacao
        falhou, em vez de seguir com um catalogo incompleto.
        """
        response = httpx.post(
            f"{self._base_url}/internal/v1/index",
            json={
                "documents": [
                    {"document_version": doc.document_version, "text": doc.text}
                    for doc in documents
                ]
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        return [IndexReport(**report) for report in response.json()["reports"]]


def get_ai_client() -> AiClient:
    settings = get_settings()
    return AiClient(base_url=settings.ai_base_url)
