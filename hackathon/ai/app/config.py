"""Configuracao do modulo ai via variaveis de ambiente.

DOCUMENTS_DIR aponta para o volume compartilhado com o backend
(``documents-data``, montado em ``/data/documents`` nos dois servicos
pelo docker-compose.yml). E onde ``ai.index`` escreve o texto
"extraido" (copiado, sem OCR/parsing real - ver app/routes/index.py).

``embedder`` (issue #69) e o mesmo toggle ``EMBEDDER`` ja existente no
backend (app/config.py::Settings.embedder, default ``"fake"``,
decisao i2-model-serving) - reusado aqui, nao um nome novo de variavel.
``"fake"`` mantem o adapter de fixtures (sem credenciais AWS, ver
app/routes/index.py e app/routes/search.py); ``"bedrock"`` liga o
pipeline real (chunking.py + embeddings.py + vector_store.py), unico
valor documentado em i7-reproducibility.md para o modo com credenciais
Bedrock reais.

``opensearch_url`` ja esta wired no docker-compose.yml
(``OPENSEARCH_URL=http://opensearch:9200``) desde o scaffold TB1 - so
sem uso real ate esta issue.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


@dataclass(frozen=True)
class Settings:
    documents_dir: str
    embedder: str
    opensearch_url: str
    dynamodb_table_process_themes: str
    dynamodb_endpoint_url: Optional[str]
    aws_region: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        documents_dir=os.environ.get("DOCUMENTS_DIR", "/data/documents"),
        embedder=os.environ.get("EMBEDDER", "fake"),
        opensearch_url=os.environ.get("OPENSEARCH_URL", "http://opensearch:9200"),
        dynamodb_table_process_themes=os.environ.get("DYNAMODB_TABLE_PROCESS_THEMES", "capiwatt-process-classification"),
        dynamodb_endpoint_url=os.environ.get("DYNAMODB_ENDPOINT_URL"),
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
    )

settings = get_settings()
