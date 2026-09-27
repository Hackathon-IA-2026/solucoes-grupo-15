"""Cliente HTTP fino para o modulo ai.

Invariante de arquitetura (vale desde o Ticket 1): o backend nunca
importa o modulo ai diretamente, so fala com ele por HTTP contra
/internal/v1/*. Ticket 2 adicionou ``index`` (contrato do port
VectorService, issue #16). Ticket 3 adiciona ``search`` (issue #19):
o backend so repassa a ``query``/``top_k`` - o ai resolve sozinho
contra o proprio fixture declarativo e devolve hits crus, ainda nao
agrupados por familia (o agrupamento e feito em
app/routes/search.py). A issue #69 adiciona ``reindex`` (mesma forma
de ``index``, ver ``reindex`` abaixo) e passa a enviar ``family_id``/
``corpus_version`` por documento em ``index``/``reindex`` - o ai real
(``EMBEDDER=bedrock``) precisa dos dois para gravar/filtrar no indice
vetorial (contrato: "family_id/document_version aparecem no indice so
como atributos de filtro"). O adapter de fixture (``EMBEDDER=fake``)
continua ignorando os dois campos, exatamente como antes. A issue #92
adiciona ``similar_families`` e ``references[]`` no ``IndexReport`` -
candidatos de arestas que app/ai_relations.py resolve e grava em
``document_relations``. ``reassign_family`` fica para tickets futuros.
"""

from dataclasses import dataclass

import httpx
from pydantic import BaseModel

from app.config import get_settings


@dataclass(frozen=True)
class IndexDocumentPayload:
    """Um documento a indexar: document_version + texto ja pronto.

    ``family_id``/``corpus_version`` (issue #69) sao redundantes por
    documento dentro de um mesmo lote (o contrato fala em
    ``index(corpus_version, documents[])``, mas o cliente HTTP daqui
    nunca mudou de assinatura - ``index(documents)`` continua igual,
    para nao quebrar os dublês de ``AiClient`` dos testes existentes) -
    o ai real (EMBEDDER=bedrock) usa os dois so como atributos de
    filtro/particionamento no indice vetorial, nunca como fonte de
    verdade do catalogo (que continua exclusivamente do backend).
    """

    document_version: str
    text: str
    family_id: str | None = None
    corpus_version: str | None = None


class AiReference(BaseModel):
    """Referencia explicita encontrada pelo ai no texto (issue #92):
    identificador cru, tipo fino opcional e localizador (``chunk_id``)."""

    identifier_raw: str
    relation_type: str | None = None
    locator: str


class IndexReport(BaseModel):
    """Espelha o IndexReport devolvido por POST /internal/v1/index."""

    document_version: str
    extracted_text_locator: str
    chunks_indexed: int
    model_version: str
    # None no modo fake - ver ai/app/routes/index.py::IndexReport (issue #73).
    total_input_tokens: int | None = None
    references: list[AiReference] = []


class AiSimilarFamily(BaseModel):
    """Um candidato de ``similar_families`` (issue #92)."""

    family_id: str
    score: float


class AiSearchHit(BaseModel):
    """Um hit cru devolvido por POST /internal/v1/search.

    Ainda nao agrupado por familia - o agrupamento por ``family_id``
    (face = versao mais recente, chunks etiquetados por versao) e
    responsabilidade exclusiva do backend (app/routes/search.py),
    nunca deste cliente nem do ai.

    ``chunk_id``/``chunk_index`` (issue #96) identificam o chunk de forma
    estavel: ``chunk_id`` e o id do chunk no indice do ai e
    ``chunk_index`` o indice real do chunk dentro do documento (0-based),
    ja resolvido pelo ai - o backend nunca faz parsing do ``chunk_id``.
    """

    family_id: str
    document_version: str
    chunk_id: str
    chunk_index: int
    excerpt: str
    score: float


class AiSearchResponse(BaseModel):
    """Espelha a resposta de POST /internal/v1/search."""

    hits: list[AiSearchHit]
    model_version: str


class AiTheme(BaseModel):
    """Espelha a taxonomia de tema devolvida por /internal/v1/themes."""

    tema_id: str
    tema_nome: str
    descricao: str = ""
    tipos_processo: list[str] = []


class AiClient:
    """Cliente tipado a partir dos nomes de operacao do port VectorService."""

    def __init__(self, base_url: str, timeout: float = 10.0, index_timeout: float = 900.0) -> None:
        """``timeout`` vale para ``health``/``search``; ``index_timeout``
        para ``index``/``reindex``, que fazem uma chamada Bedrock por
        chunk dentro de uma unica requisicao (EMBEDDER=bedrock) - 10 s
        estourou no primeiro ``POST /v1/ingestions`` na AWS (issue #106).
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._index_timeout = index_timeout

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
            json={"documents": [_document_payload(doc) for doc in documents]},
            timeout=self._index_timeout,
        )
        response.raise_for_status()
        return [IndexReport(**report) for report in response.json()["reports"]]

    def reindex(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        """Chama POST /internal/v1/reindex no ai (issue #69).

        Mesma forma de ``index``, mas o ai ignora qualquer cache de
        idempotencia e reconstroi o indice do zero so com os
        documentos enviados nesta chamada - quem chama precisa reenviar
        o catalogo inteiro que quer preservado (o ai nunca le o
        catalogo do backend por conta propria).
        """
        response = httpx.post(
            f"{self._base_url}/internal/v1/reindex",
            json={"documents": [_document_payload(doc) for doc in documents]},
            timeout=self._index_timeout,
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

    def similar_families(self, family_id: str, top_k: int) -> list[AiSimilarFamily]:
        """Chama GET /internal/v1/families/{family_id}/similar (issue #92).

        Devolve so candidatos crus (``family_id``, ``score``) - aplicar os
        limiares e gravar arestas e de app/ai_relations.py. Propaga erros
        HTTP/rede, como ``index``.
        """
        response = httpx.get(
            f"{self._base_url}/internal/v1/families/{family_id}/similar",
            params={"top_k": top_k},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return [AiSimilarFamily(**item) for item in response.json()["similar"]]

    def get_themes(self) -> list[AiTheme]:
        """Chama GET /internal/v1/themes no ai e devolve a lista de temas."""
        response = httpx.get(
            f"{self._base_url}/internal/v1/themes",
            timeout=self._timeout,
        )
        response.raise_for_status()
        return [AiTheme(**item) for item in response.json()]


def _document_payload(doc: IndexDocumentPayload) -> dict[str, object]:
    payload: dict[str, object] = {"document_version": doc.document_version, "text": doc.text}
    if doc.family_id is not None:
        payload["family_id"] = doc.family_id
    if doc.corpus_version is not None:
        payload["corpus_version"] = doc.corpus_version
    return payload


def get_ai_client() -> AiClient:
    settings = get_settings()
    return AiClient(base_url=settings.ai_base_url)
