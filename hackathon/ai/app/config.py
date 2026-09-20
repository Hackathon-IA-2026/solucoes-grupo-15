"""Configuracao do modulo ai via variaveis de ambiente.

DOCUMENTS_DIR aponta para o volume compartilhado com o backend
(``documents-data``, montado em ``/data/documents`` nos dois servicos
pelo docker-compose.yml). E onde ``ai.index`` escreve o texto
"extraido" (copiado, sem OCR/parsing real - ver app/routes/index.py).
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    documents_dir: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        documents_dir=os.environ.get("DOCUMENTS_DIR", "/data/documents"),
    )
