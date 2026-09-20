"""Ponto de entrada do app FastAPI do modulo ai.

Ticket 1 (TB1) implementou o health check interno
(/internal/v1/health). Ticket 2 adicionou a operacao ``index`` do port
VectorService (/internal/v1/index, ver app/routes/index.py) - um
adapter demo, sem embeddings/modelo reais. Ticket 3 adiciona ``search``
(/internal/v1/search, ver app/routes/search.py), tambem um adapter
demo: resolve contra um mapeamento declarativo fixo de fixture, sem
busca vetorial real. As demais operacoes do port (similar_families,
reassign_family, delete/reindex) pertencem a tickets futuros.
"""

from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.index import router as index_router
from app.routes.search import router as search_router


def create_app() -> FastAPI:
    app = FastAPI(title="CapiWatt Lens - ai")
    app.state.index_store = {}
    app.include_router(health_router)
    app.include_router(index_router)
    app.include_router(search_router)
    return app


app = create_app()
