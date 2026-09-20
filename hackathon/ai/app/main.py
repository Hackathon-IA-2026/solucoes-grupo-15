"""Ponto de entrada do app FastAPI do modulo ai.

Neste ticket (TB1 Ticket 1) o unico contrato implementado e o health
check interno (/internal/v1/health). As demais operacoes do port
VectorService (index, search, similar_families, reassign_family,
delete/reindex) pertencem a tickets futuros.
"""

from fastapi import FastAPI

from app.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="CapiWatt Lens - ai")
    app.include_router(health_router)
    return app


app = create_app()
