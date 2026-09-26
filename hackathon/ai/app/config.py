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


@dataclass(frozen=True)
class Settings:
    documents_dir: str
    embedder: str
    opensearch_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        documents_dir=os.environ.get("DOCUMENTS_DIR", "/data/documents"),
        embedder=os.environ.get("EMBEDDER", "fake"),
        opensearch_url=os.environ.get("OPENSEARCH_URL", "http://opensearch:9200"),
    )
