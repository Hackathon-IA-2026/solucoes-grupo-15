"""Setup simples do SQLAlchemy para o catalogo do backend.

Um ``Base.metadata.create_all()`` no startup do app basta neste estagio
do hackathon (catalogo pequeno, schema ainda se formando) - sem Alembic
por ora.

O acesso a sessao de banco e sempre por injecao de dependencia
(``get_db_session``), nunca por import direto de um singleton, para que
testes possam trocar a session factory (Postgres de teste) via
``app.dependency_overrides`` - o mesmo padrao ja usado para
``get_ai_client``.
"""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def get_db_session(request: Request) -> Iterator[Session]:
    """Dependencia FastAPI para uma sessao de banco ligada ao catalogo.

    Le a session factory de ``app.state.db_session_factory``,
    configurada em ``create_app()`` a partir de
    ``Settings.database_url``. Faz commit ao final se nao houve
    excecao; caso contrario, rollback.
    """
    session_factory = request.app.state.db_session_factory
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
