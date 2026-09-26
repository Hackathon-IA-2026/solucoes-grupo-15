"""Configuracao do modulo ai via variaveis de ambiente.

DOCUMENTS_DIR aponta para o volume compartilhado com o backend
(``documents-data``, montado em ``/data/documents`` nos dois servicos
pelo docker-compose.yml). E onde ``ai.index`` escreve o texto
"extraido" (copiado, sem OCR/parsing real - ver app/routes/index.py).
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


@dataclass(frozen=True)
class Settings:
    documents_dir: str
    dynamodb_table_process_themes: str
    dynamodb_endpoint_url: Optional[str]
    aws_region: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        documents_dir=os.environ.get("DOCUMENTS_DIR", "/data/documents"),
        dynamodb_table_process_themes=os.environ.get("DYNAMODB_TABLE_PROCESS_THEMES", "capiwatt-process-classification"),
        dynamodb_endpoint_url=os.environ.get("DYNAMODB_ENDPOINT_URL"),
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
    )

settings = get_settings()
