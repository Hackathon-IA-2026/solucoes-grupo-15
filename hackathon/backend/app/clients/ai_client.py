"""Cliente HTTP fino para o modulo ai.

Invariante de arquitetura (vale desde o Ticket 1): o backend nunca
importa o modulo ai diretamente, so fala com ele por HTTP contra
/internal/v1/*. Ticket 2 adicionou ``index`` (contrato do port
VectorService, issue #16). Ticket 3 adiciona ``search`` (issue #19):
o backend so repassa a ``query``/``top_k`` - o ai resolve sozinho
contra o proprio fixture declarativo e devolve hits crus, ainda nao
agrupados por familia (o agrupamento e feito em
app/routes/search.py). As demais operacoes (similar_families,
reassign_family, delete/reindex) ficam para tickets futuros.
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


class AiSearchHit(BaseModel):
    """Um hit cru devolvido por POST /internal/v1/search.

    Ainda nao agrupado por familia - o agrupamento por ``family_id``
    (face = versao mais recente, chunks etiquetados por versao) e
    responsabilidade exclusiva do backend (app/routes/search.py),
    nunca deste cliente nem do ai.
    """

    family_id: str
    document_version: str
    excerpt: str
    score: float


class AiSearchResponse(BaseModel):
    """Espelha a resposta de POST /internal/v1/search."""

    hits: list[AiSearchHit]
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

    def search(self, query: str, top_k: int | None = None) -> AiSearchResponse:
        """Chama POST /internal/v1/search no ai e devolve os hits crus.

        So repassa ``query``/``top_k`` - o ai resolve sozinho contra o
        proprio fixture declarativo (nao ha payload de dados de busca
        aqui, ao contrario de ``index``). Como ``index``, propaga
        erros HTTP/rede - quem busca (POST /v1/search) precisa saber
        se a chamada ao ai falhou, em vez de devolver um envelope de
        busca incompleto/enganoso.
        """
        payload: dict[str, object] = {"query": query}
        if top_k is not None:
            payload["top_k"] = top_k
        response = httpx.post(
            f"{self._base_url}/internal/v1/search",
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        return AiSearchResponse(**response.json())


def get_ai_client() -> AiClient:
    settings = get_settings()
    return AiClient(base_url=settings.ai_base_url)
