"""Configuracao do backend via variaveis de ambiente.

Valores padrao seguem a decisao i2-model-serving (local, sem
credenciais AWS por padrao): EMBEDDER=fake e MAILER=preview. Nenhuma
variavel de credencial AWS e lida aqui - troca de adapter real
(Bedrock/SES) fica para tickets futuros.

``default_corpus_version`` (Ticket 3, issue #19) e o fallback do
envelope de POST /v1/search quando ``results`` fica vazio (nenhum hit
devolvido pelo ai, logo nenhuma familia da qual derivar o
``corpus_version`` do catalogo) - hoje coincide com o
``corpus_version`` do corpus fixture (app/fixtures/demo_corpus.json,
"demo-v1"), mas fica configuravel por variavel de ambiente para nao
prender o codigo a esse valor.
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    ai_base_url: str
    embedder: str
    mailer: str
    database_url: str
    default_corpus_version: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        ai_base_url=os.environ.get("AI_BASE_URL", "http://ai:8000"),
        embedder=os.environ.get("EMBEDDER", "fake"),
        mailer=os.environ.get("MAILER", "preview"),
        database_url=os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://capiwatt:capiwatt@postgres:5432/capiwatt",
        ),
        default_corpus_version=os.environ.get("DEFAULT_CORPUS_VERSION", "demo-v1"),
    )
