"""Ponto de entrada do app FastAPI do modulo backend.

Neste ticket (TB1 Ticket 1) o unico contrato implementado e o health
check publico (/v1/health), que verifica o ai por HTTP. A API /v1/*
completa (catalogo, busca, grafo, notificacoes, feedback) pertence a
tickets futuros.
"""

from fastapi import FastAPI

from app.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="CapiWatt Lens - backend")
    app.include_router(health_router)
    return app


app = create_app()
