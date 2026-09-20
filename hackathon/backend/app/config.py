"""Configuracao do backend via variaveis de ambiente.

Valores padrao seguem a decisao i2-model-serving (local, sem
credenciais AWS por padrao): EMBEDDER=fake e MAILER=preview. Nenhuma
variavel de credencial AWS e lida aqui - troca de adapter real
(Bedrock/SES) fica para tickets futuros.
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    ai_base_url: str
    embedder: str
    mailer: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        ai_base_url=os.environ.get("AI_BASE_URL", "http://ai:8000"),
        embedder=os.environ.get("EMBEDDER", "fake"),
        mailer=os.environ.get("MAILER", "preview"),
    )
