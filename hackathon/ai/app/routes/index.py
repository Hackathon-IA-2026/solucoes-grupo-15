"""Rota interna de indexacao (adapter demo) do modulo ai.

Cobre, para o Ticket 2 (TB1), a operacao ``index`` do port
VectorService (issue #16): o backend monta o payload a partir do
corpus de fixtures demo e chama esta rota - o ai nunca le o arquivo de
fixture diretamente, so processa o que recebe por HTTP.

Para cada documento recebido, "extrai" o texto = copia o ``text`` ja
fornecido para um arquivo em ``DOCUMENTS_DIR/<document_version>/extracted.txt``
(sem OCR, sem parsing real). ``chunks_indexed`` e so a contagem de
blocos separados por linha em branco no texto - a fixture ja vem
pre-dividida assim; isto NAO e uma estrategia de chunking real.
``model_version`` de resposta e a constante fixa ``fixture-demo`` (nao
ha modelo real neste ticket; buscas futuras devem reusar esta mesma
constante no envelope de resposta).

Idempotente por ``(document_version, model_version)``: reindexar a
mesma versao nao reescreve o arquivo nem reprocessa - devolve o mesmo
IndexReport de antes. O estado de idempotencia vive em memoria do
processo (``app.state.index_store``), o que basta para este estagio do
hackathon (nao ha reinicio do ai durante a demo).
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/internal/v1", tags=["internal"])

MODEL_VERSION = "fixture-demo"


class IndexDocumentIn(BaseModel):
    document_version: str
    text: str


class IndexRequest(BaseModel):
    documents: list[IndexDocumentIn]


class IndexReport(BaseModel):
    document_version: str
    extracted_text_locator: str
    chunks_indexed: int
    model_version: str


class IndexResponse(BaseModel):
    reports: list[IndexReport]


def get_documents_root() -> Path:
    """Dependencia FastAPI para a raiz do volume de documentos.

    Testes sobrescrevem esta dependencia (dependency_overrides) para
    apontar a um diretorio temporario, em vez do volume real montado em
    producao/Docker.
    """
    return Path(get_settings().documents_dir)


def get_index_store(request: Request) -> dict[tuple[str, str], IndexReport]:
    """Estado de idempotencia em memoria, escopado por instancia do app."""
    return request.app.state.index_store


@router.post("/index", response_model=IndexResponse)
def index_documents(
    payload: IndexRequest,
    documents_root: Path = Depends(get_documents_root),
    store: dict[tuple[str, str], IndexReport] = Depends(get_index_store),
) -> IndexResponse:
    reports = [_index_one(document, documents_root, store) for document in payload.documents]
    return IndexResponse(reports=reports)


def _index_one(
    document: IndexDocumentIn,
    documents_root: Path,
    store: dict[tuple[str, str], IndexReport],
) -> IndexReport:
    key = (document.document_version, MODEL_VERSION)
    cached = store.get(key)
    if cached is not None:
        return cached

    version_dir = documents_root / document.document_version
    version_dir.mkdir(parents=True, exist_ok=True)
    extracted_path = version_dir / "extracted.txt"
    extracted_path.write_text(document.text, encoding="utf-8")

    chunks_indexed = len([block for block in document.text.split("\n\n") if block.strip()])

    report = IndexReport(
        document_version=document.document_version,
        extracted_text_locator=str(extracted_path),
        chunks_indexed=chunks_indexed,
        model_version=MODEL_VERSION,
    )
    store[key] = report
    return report
