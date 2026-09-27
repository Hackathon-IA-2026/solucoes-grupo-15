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
Ticket 7 adiciona o feedback 👍/👎 sobre cards de resultado de busca
(ver app/routes/feedback.py): POST /v1/feedback (persiste o voto) e
GET /v1/feedback (lista para conferencia manual). Ticket 8 adiciona
notificacoes + previa de e-mail (ver app/routes/notifications.py):
escolha de escopo por usuario, geracao de notificacao a partir da
ingestao (app/notifications.py::run_notifications) e o port ``Mailer``
(app/mailer.py). Issue #103 adiciona a linha de log JSON por requisicao
a /v1/* no stdout (ver app/request_log.py). Issue #104 adiciona
``AUTH_MODE=none|cognito`` (ver app/auth.py): em ``cognito`` todo router
exceto o de health exige ``get_identity``, e ingestao e reset demo exigem
o grupo ``admin``.

O engine/session factory do catalogo sao criados aqui a partir de
Settings.database_url e guardados em app.state; testes substituem a
dependencia get_db_session inteira (dependency_overrides), entao nunca
dependem deste engine "de producao" apontar para um banco valido.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.auth import build_cognito_verifier, get_identity, require_admin, validate_auth_settings
from app.config import get_settings
from app.db import Base, make_engine, make_session_factory
from app.request_log import RequestLogMiddleware
from app.routes.demo import router as demo_router
from app.routes.documents import router as documents_router
from app.routes.families import router as families_router
from app.routes.feedback import router as feedback_router
from app.routes.health import router as health_router
from app.routes.ingestions import router as ingestions_router
from app.routes.notifications import router as notifications_router
from app.routes.opinion import router as opinion_router
from app.routes.opinions import router as opinions_router
from app.routes.relations import router as relations_router
from app.routes.search import router as search_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=app.state.db_engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    validate_auth_settings(settings)
    engine = make_engine(settings.database_url)

    app = FastAPI(title="CapiWatt Lens - backend", lifespan=_lifespan)
    app.state.db_engine = engine
    app.state.db_session_factory = make_session_factory(engine)
    app.state.auth_mode = settings.auth_mode
    app.state.token_verifier = (
        build_cognito_verifier(settings) if settings.auth_mode == "cognito" else None
    )
    app.add_middleware(RequestLogMiddleware)

    authenticated = [Depends(get_identity)]
    admin_only = [Depends(require_admin)]
    app.include_router(health_router)
    app.include_router(demo_router, dependencies=admin_only)
    app.include_router(ingestions_router, dependencies=admin_only)
    app.include_router(search_router, dependencies=authenticated)
    app.include_router(documents_router, dependencies=authenticated)
    app.include_router(families_router, dependencies=authenticated)
    # opinions_router deve vir antes de relations_router (catch-all)
    app.include_router(opinions_router, dependencies=authenticated)
    app.include_router(relations_router, dependencies=authenticated)
    app.include_router(feedback_router, dependencies=authenticated)
    app.include_router(notifications_router, dependencies=authenticated)
    app.include_router(opinion_router, dependencies=authenticated)
    return app


app = create_app()
