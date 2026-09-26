"""Rota interna de indexacao do modulo ai.

Cobre a operacao ``index`` do port VectorService (issue #16), em dois
modos, escolhidos por ``Settings.embedder`` (variavel de ambiente
``EMBEDDER``, ja existente - ver app/config.py):

- ``EMBEDDER=fake`` (default, Ticket 2/TB1): adapter demo original, sem
  embeddings/modelo reais. Para cada documento, "extrai" o texto = copia
  o ``text`` ja fornecido para ``DOCUMENTS_DIR/<document_version>/extracted.txt``
  e conta blocos separados por linha em branco - preservado
  byte-a-byte para nao quebrar o modo fixture (issue #69, AC "modo
  fixture continua funcionando sem credenciais AWS"). ``model_version``
  de resposta e a constante fixa ``MODEL_VERSION = "fixture-demo"``.

- ``EMBEDDER=bedrock`` (issue #69): pipeline real. Chunking estrutural
  (app/chunking.py, 600/800/100 tokens) sobre o texto recebido, um
  embedding Titan V2 por chunk (app/embeddings.py::BedrockEmbedder) e
  upsert desses chunks no indice vetorial (app/vector_store.py, um
  indice OpenSearch por model_version). O texto recebido tambem e
  escrito no mesmo localizador que o modo fake usa (locator de texto
  extraido - o ai nao faz OCR/parsing de PDF aqui, so grava o que
  recebeu). ``model_version`` de resposta e
  ``app.embeddings.MODEL_VERSION`` (identifica modelo/regiao/dimensoes/
  normalizacao). Requer ``family_id`` e ``corpus_version`` por
  documento (contrato: "family_id/document_version aparecem no indice
  so como atributos de filtro"; "index(corpus_version, documents[])") -
  ausencia de qualquer um dos dois e erro 422 (nao ha como indexar de
  verdade sem eles).

Idempotente por ``(document_version, model_version)`` nos dois modos:
reindexar a mesma versao com o mesmo ``model_version`` nao reescreve o
locator nem reprocessa - devolve o mesmo IndexReport de antes. O estado
de idempotencia vive em memoria do processo (``app.state.index_store``,
chaveado por ``(document_version, model_version)`` - dois modelos
diferentes para o mesmo document_version nunca colidem no cache nem no
indice, cada um vive no seu proprio namespace).

``POST /internal/v1/reindex`` (app/routes/reindex.py) reusa
``_index_one`` ignorando o cache, para reconstruir do zero.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.chunking import chunk_document
from app.config import get_settings
from app.embeddings import (
    DIMENSIONS,
    BedrockEmbedder,
    get_bedrock_runtime_client,
)
from app.embeddings import (
    MODEL_VERSION as REAL_MODEL_VERSION,
)
from app.vector_store import (
    ChunkDoc,
    OpenSearchVectorStore,
    VectorStore,
    index_name_for_model_version,
)

router = APIRouter(prefix="/internal/v1", tags=["internal"])

MODEL_VERSION = "fixture-demo"


class IndexDocumentIn(BaseModel):
    document_version: str
    text: str
    # Obrigatorios so no modo EMBEDDER=bedrock (validado em _index_one_real,
    # nao aqui no schema) - o modo fake nunca precisou deles, e testes
    # existentes do modo fake (tests/test_index.py) nao os enviam.
    family_id: str | None = None
    corpus_version: str | None = None


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


def get_embedder() -> BedrockEmbedder:
    """Dependencia FastAPI para o adapter de embeddings real.

    Testes sobrescrevem com um dublê (ver
    hackathon/ai/tests/test_index_real.py) - nunca chamam Bedrock de
    verdade na suite automatizada.
    """
    return BedrockEmbedder(get_bedrock_runtime_client())


def get_vector_store() -> VectorStore:
    """Dependencia FastAPI para o indice vetorial real (OpenSearch).

    Testes sobrescrevem com ``InMemoryVectorStore`` (app/vector_store.py)
    - nunca abrem conexao de rede na suite automatizada.
    """
    return OpenSearchVectorStore(get_settings().opensearch_url)


@router.post("/index", response_model=IndexResponse)
def index_documents(
    payload: IndexRequest,
    documents_root: Path = Depends(get_documents_root),
    store: dict[tuple[str, str], IndexReport] = Depends(get_index_store),
    embedder: BedrockEmbedder = Depends(get_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
) -> IndexResponse:
    settings = get_settings()
    if settings.embedder == "bedrock":
        reports = [
            _index_one_real(document, documents_root, store, embedder, vector_store)
            for document in payload.documents
        ]
    else:
        reports = [
            _index_one_fake(document, documents_root, store) for document in payload.documents
        ]
    return IndexResponse(reports=reports)


def _write_locator(document_version: str, text: str, documents_root: Path) -> Path:
    version_dir = documents_root / document_version
    version_dir.mkdir(parents=True, exist_ok=True)
    extracted_path = version_dir / "extracted.txt"
    extracted_path.write_text(text, encoding="utf-8")
    return extracted_path


def _index_one_fake(
    document: IndexDocumentIn,
    documents_root: Path,
    store: dict[tuple[str, str], IndexReport],
) -> IndexReport:
    key = (document.document_version, MODEL_VERSION)
    cached = store.get(key)
    if cached is not None:
        return cached

    extracted_path = _write_locator(document.document_version, document.text, documents_root)
    chunks_indexed = len([block for block in document.text.split("\n\n") if block.strip()])

    report = IndexReport(
        document_version=document.document_version,
        extracted_text_locator=str(extracted_path),
        chunks_indexed=chunks_indexed,
        model_version=MODEL_VERSION,
    )
    store[key] = report
    return report


def _index_one_real(
    document: IndexDocumentIn,
    documents_root: Path,
    store: dict[tuple[str, str], IndexReport],
    embedder: BedrockEmbedder,
    vector_store: VectorStore,
    *,
    force: bool = False,
) -> IndexReport:
    key = (document.document_version, REAL_MODEL_VERSION)
    if not force:
        cached = store.get(key)
        if cached is not None:
            return cached

    if not document.family_id or not document.corpus_version:
        raise HTTPException(
            status_code=422,
            detail=(
                "family_id e corpus_version sao obrigatorios para indexar com "
                "EMBEDDER=bedrock (documento sem um dos dois: "
                f"{document.document_version!r})"
            ),
        )

    chunks = chunk_document(document.text, document.document_version)
    index_name = index_name_for_model_version(REAL_MODEL_VERSION)
    vector_store.ensure_index(index_name, DIMENSIONS)
    # Upsert por document_version: remove chunks antigos dessa versao antes
    # de gravar os novos, para o caso de reprocessar apos perda do cache em
    # memoria (ex.: restart do processo) com texto diferente - a contagem de
    # chunks/pontuacoes nunca mistura resto de uma indexacao anterior.
    vector_store.delete_document(index_name, document.document_version)

    chunk_docs = [
        ChunkDoc(
            chunk_id=chunk.chunk_id,
            document_version=document.document_version,
            family_id=document.family_id,
            corpus_version=document.corpus_version,
            model_version=REAL_MODEL_VERSION,
            section=chunk.section,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            text=chunk.text,
            embedding=embedder.embed_text(chunk.text).vector,
        )
        for chunk in chunks
    ]
    vector_store.index_chunks(index_name, chunk_docs)

    extracted_path = _write_locator(document.document_version, document.text, documents_root)

    report = IndexReport(
        document_version=document.document_version,
        extracted_text_locator=str(extracted_path),
        chunks_indexed=len(chunks),
        model_version=REAL_MODEL_VERSION,
    )
    store[key] = report
    return report
