"""Ponto de entrada do app FastAPI do modulo ai.

Ticket 1 (TB1) implementou o health check interno
(/internal/v1/health). Ticket 2 adicionou a operacao ``index`` do port
VectorService (/internal/v1/index, ver app/routes/index.py). Ticket 3
adicionou ``search`` (/internal/v1/search, ver app/routes/search.py).
Ate a issue #69, os dois eram adapters demo (fixture), sem busca
vetorial real. A issue #69 torna os dois reais por tras do mesmo toggle
``EMBEDDER`` (ver app/config.py) e adiciona ``reindex``
(/internal/v1/reindex, ver app/routes/reindex.py). As demais operacoes
do port (similar_families, reassign_family) continuam fora de escopo,
para tickets futuros.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.cached_embeddings import EmbeddingNotCached
from app.routes.health import router as health_router
from app.routes.index import router as index_router
from app.routes.reindex import router as reindex_router
from app.routes.search import router as search_router
from app.routes.process_classification import router as process_classification_router


def create_app() -> FastAPI:
    app = FastAPI(title="CapiWatt Lens - ai")
    app.state.index_store = {}
    app.include_router(health_router)
    app.include_router(index_router)
    app.include_router(search_router)
    app.include_router(reindex_router)
    app.include_router(process_classification_router)
    app.add_exception_handler(EmbeddingNotCached, _embedding_not_cached_handler)
    return app


async def _embedding_not_cached_handler(_: Request, exc: EmbeddingNotCached) -> JSONResponse:
    # EMBEDDER=cached (issue #88): texto sem vetor pre-computado e entrada
    # que este modo nao sabe processar, nao falha interna do servico.
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app = create_app()
