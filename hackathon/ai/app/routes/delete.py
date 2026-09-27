"""Rota interna ``delete(document_version)`` do port VectorService (issue #98).

``DELETE /internal/v1/documents/{document_version}`` tira uma versao do
indice derivado do ``model_version`` corrente e devolve
``{document_version, model_version, chunks_deleted}``. O path segue a
convencao de ``reassign_family`` (``/internal/v1/documents/{id}/family``);
nao reintroduz o ``GET /internal/v1/documents/{id}`` (``get_document``),
removido do port pela issue-15.

Nos dois modos escolhidos por ``EMBEDDER`` (mesmo toggle de
app/routes/index.py):

- Pipeline real (``bedrock``/``cached``): apaga os chunks da versao no
  indice OpenSearch, grava um tombstone para ela nos vetores brutos
  (app/raw_vectors.py; o arquivo e append-only, entao as linhas antigas
  continuam no disco, mas o replay - e com ele o reindex offline
  ``tools/case1_recall/reindex_from_raw_vectors.py`` - nao a ressuscita) e
  esquece o relatorio cacheado de ``index``, para que um ``index``
  seguinte da mesma versao grave os chunks de novo.
- Fixture (``fake``): nao ha indice vetorial (a busca le um mapeamento
  declarativo, que o delete nao altera). O "indice" e o cache de
  relatorios de ``index``: a versao e esquecida e ``chunks_deleted`` e o
  ``chunks_indexed`` que ela tinha.

Decisoes conservadoras (issue #98, registradas no contrato):

- Idempotente: versao desconhecida ou ja apagada -> 200 com
  ``chunks_deleted: 0``, nunca 404. Um retry do backend nao vira erro.
- O texto em ``extracted_text_locator`` NAO e apagado: esta registrado no
  catalogo do backend, que e dono do ciclo de vida da versao, e e o que a
  pagina do documento le. ``delete`` so mexe no derivado.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import REAL_PIPELINE_EMBEDDERS, get_settings
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.raw_vectors import RawVectorStore
from app.routes.index import (
    MODEL_VERSION,
    IndexReport,
    get_index_store,
    get_raw_vector_store,
    get_vector_store,
)
from app.vector_store import VectorStore, index_name_for_model_version

router = APIRouter(prefix="/internal/v1", tags=["internal"])


class DeleteReport(BaseModel):
    document_version: str
    model_version: str
    chunks_deleted: int


@router.delete("/documents/{document_version}", response_model=DeleteReport)
def delete_document(
    document_version: str,
    store: dict[tuple[str, str], IndexReport] = Depends(get_index_store),
    vector_store: VectorStore = Depends(get_vector_store),
    raw_vector_store: RawVectorStore = Depends(get_raw_vector_store),
) -> DeleteReport:
    if get_settings().embedder not in REAL_PIPELINE_EMBEDDERS:
        cached = store.pop((document_version, MODEL_VERSION), None)
        return DeleteReport(
            document_version=document_version,
            model_version=MODEL_VERSION,
            chunks_deleted=cached.chunks_indexed if cached is not None else 0,
        )

    index_name = index_name_for_model_version(REAL_MODEL_VERSION)
    chunks_deleted = vector_store.count_chunks_for_document(index_name, document_version)
    vector_store.delete_document(index_name, document_version)
    raw_vector_store.delete_document(document_version)
    store.pop((document_version, REAL_MODEL_VERSION), None)
    return DeleteReport(
        document_version=document_version,
        model_version=REAL_MODEL_VERSION,
        chunks_deleted=chunks_deleted,
    )
