"""Ponto de entrada do app FastAPI do modulo backend.

Ticket 1 (TB1) implementou o health check publico (/v1/health). Ticket
2 adicionou o catalogo documental (document_family, document_version) em
Postgres e POST /v1/ingestions, que le o corpus de fixtures demo e
popula o catalogo via AiClient.index (ver app/routes/ingestions.py).
Ticket 3 adiciona POST /v1/search (ver app/routes/search.py): agrupa
por familia os hits crus devolvidos por AiClient.search. Ticket 4
adiciona GET /v1/documents/{family_id} (ver app/routes/documents.py):
cabecalho + linha do tempo de versoes + texto extraido da versao
selecionada, para a pagina de familia do frontend. Ticket 5 adiciona o
grafo de relacoes (ver app/routes/relations.py):
GET /v1/documents/{node_id}/graph e GET /v1/processos/{processo_id}.
A API /v1/* completa (notificacoes, feedback) pertence a tickets
futuros.

O engine/session factory do catalogo sao criados aqui a partir de
Settings.database_url e guardados em app.state; testes substituem a
dependencia get_db_session inteira (dependency_overrides), entao nunca
dependem deste engine "de producao" apontar para um banco valido.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import Base, make_engine, make_session_factory
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router
from app.routes.ingestions import router as ingestions_router
from app.routes.relations import router as relations_router
from app.routes.search import router as search_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=app.state.db_engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    engine = make_engine(settings.database_url)

    app = FastAPI(title="CapiWatt Lens - backend", lifespan=_lifespan)
    app.state.db_engine = engine
    app.state.db_session_factory = make_session_factory(engine)
    app.include_router(health_router)
    app.include_router(ingestions_router)
    app.include_router(search_router)
    app.include_router(documents_router)
    app.include_router(relations_router)
    return app


app = create_app()
