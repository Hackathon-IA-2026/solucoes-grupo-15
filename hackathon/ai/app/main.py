"""Ponto de entrada do app FastAPI do modulo ai.

Ticket 1 (TB1) implementou o health check interno
(/internal/v1/health). Ticket 2 adiciona a operacao ``index`` do port
VectorService (/internal/v1/index, ver app/routes/index.py) - um
adapter demo, sem embeddings/modelo reais. As demais operacoes do port
(search, similar_families, reassign_family, delete/reindex) pertencem
a tickets futuros.
"""

from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.index import router as index_router


def create_app() -> FastAPI:
    app = FastAPI(title="CapiWatt Lens - ai")
    app.state.index_store = {}
    app.include_router(health_router)
    app.include_router(index_router)
    return app


app = create_app()
