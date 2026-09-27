"""Infra da suite e2e backend <-> banco vetorial (issue #88).

Sobe ``docker-compose.e2e.yml`` (backend, ai, Postgres e OpenSearch
reais) uma vez por sessao, ingere o caso 1 pelo backend e derruba tudo
no fim (``down -v``). Nenhuma credencial AWS e usada: o ai roda com
``EMBEDDER=cached`` sobre os vetores brutos da #73.

Variaveis de ambiente:

- ``E2E_RAW_VECTORS_PATH``: JSONL de vetores brutos da #73 (default:
  ``hackathon/.pipeline-output/documents/_raw_vectors/<model_version>.jsonl``,
  fora do git - gerado por ``tools/case1_recall/seed_and_measure.py``).
- ``E2E_QUERY_VECTOR_PATH``: vetor da consulta da Carolina (default: o do
  protototipo da #60, versionado).
- ``E2E_EXTERNAL_STACK=1``: nao sobe/derruba nada; usa ``E2E_BACKEND_URL``,
  ``E2E_AI_URL`` e ``E2E_OPENSEARCH_URL`` (ex.: stack ja de pe, ou a stack
  AWS da #89 no futuro).
- ``E2E_KEEP_STACK=1``: nao derruba a stack no fim (depuracao).

Os testes so falam HTTP com backend/ai/OpenSearch - nunca importam
``backend/app`` nem ``ai/app`` (os dois pacotes se chamam ``app`` e
colidiriam; ver tools/case1_recall/seed_and_measure.py).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

HACKATHON_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HACKATHON_DIR.parent
E2E_DIR = HACKATHON_DIR / "tests_e2e"
COMPOSE_FILE = E2E_DIR / "docker-compose.e2e.yml"
COMPOSE_PROJECT = "capiwatt-e2e"

MODEL_VERSION = "amazon.titan-embed-text-v2-us-east-1-1024d-normalized"
DEFAULT_RAW_VECTORS_PATH = (
    HACKATHON_DIR / ".pipeline-output" / "documents" / "_raw_vectors" / f"{MODEL_VERSION}.jsonl"
)
DEFAULT_QUERY_VECTOR_PATH = (
    HACKATHON_DIR / "tools" / "prototypes" / "recall_baseline" / "output" / "query.json"
)
MANIFEST_PATH = HACKATHON_DIR / ".pipeline-output" / "manifest.json"
CASE1_DATA_DIR = HACKATHON_DIR / "data" / "case-1-carolina-mmgd"

sys.path.insert(0, str(HACKATHON_DIR / "tools" / "pipeline"))
sys.path.insert(0, str(HACKATHON_DIR / "tools" / "case1_recall"))

from manifest import (  # noqa: E402
    CASE1_CORPUS_ID,
    ManifestDocument,
    _scan_case1,
    compute_corpus_version,
)


@dataclass(frozen=True)
class Stack:
    backend_url: str
    ai_url: str
    opensearch_url: str
    raw_vectors_path: Path
    managed: bool  # True quando esta suite subiu a stack via Compose
    compose_env: dict[str, str] | None = None

    def ai_search_calls(self) -> int:
        """Quantas vezes o ai recebeu POST /internal/v1/search (log de
        acesso do uvicorn) - prova que continuacao por cursor nao chama o ai."""
        logs = _compose("logs", "--no-log-prefix", "ai", capture=True, env=self.compose_env).stdout
        return sum(1 for line in logs.splitlines() if '"POST /internal/v1/search' in line)


def _compose(*args: str, capture: bool = False, env: dict | None = None):
    return subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "-f", str(COMPOSE_FILE), *args],
        check=True,
        capture_output=capture,
        text=True,
        env=env,
    )


def case1_manifest_corpus_version() -> str:
    """``corpus_version`` do caso 1 segundo o manifesto da #68: o hash de
    ``compute_corpus_version`` so sobre os documentos do caso 1. Le o
    manifesto gerado quando existe; senao varre os PDFs versionados (o
    hash e o mesmo por construcao)."""
    if MANIFEST_PATH.exists():
        records = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["documentos"]
        documents = [
            ManifestDocument.from_dict(r) for r in records if r["corpus_id"] == CASE1_CORPUS_ID
        ]
    else:
        documents = list(_scan_case1(CASE1_DATA_DIR, REPO_ROOT))
    return compute_corpus_version(documents)


@pytest.fixture(scope="session")
def stack() -> Iterator[Stack]:
    raw_vectors_path = Path(os.environ.get("E2E_RAW_VECTORS_PATH", DEFAULT_RAW_VECTORS_PATH))
    query_vector_path = Path(os.environ.get("E2E_QUERY_VECTOR_PATH", DEFAULT_QUERY_VECTOR_PATH))
    if not raw_vectors_path.exists():
        pytest.skip(
            f"vetores brutos da #73 ausentes em {raw_vectors_path} - rode "
            "tools/case1_recall/seed_and_measure.py uma vez (com Bedrock) ou aponte "
            "E2E_RAW_VECTORS_PATH para uma copia"
        )

    external = os.environ.get("E2E_EXTERNAL_STACK") == "1"
    compose_env = {
        **os.environ,
        "E2E_RAW_VECTORS_PATH": str(raw_vectors_path.resolve()),
        "E2E_QUERY_VECTOR_PATH": str(query_vector_path.resolve()),
    }
    stack = Stack(
        backend_url=os.environ.get("E2E_BACKEND_URL", "http://localhost:18000"),
        ai_url=os.environ.get("E2E_AI_URL", "http://localhost:18001"),
        opensearch_url=os.environ.get("E2E_OPENSEARCH_URL", "http://localhost:19200"),
        raw_vectors_path=raw_vectors_path,
        managed=not external,
        compose_env=compose_env,
    )
    if external:
        yield stack
        return

    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("Docker indisponivel - a suite e2e sobe a stack via Compose")

    _compose("down", "-v", "--remove-orphans", env=compose_env)
    _compose("up", "-d", "--build", "--wait", env=compose_env)
    try:
        yield stack
    finally:
        if os.environ.get("E2E_KEEP_STACK") != "1":
            _compose("down", "-v", "--remove-orphans", env=compose_env)


@pytest.fixture(scope="session")
def backend(stack: Stack) -> Iterator[httpx.Client]:
    # Ingestao/indexacao do corpus real fazem uma busca de vetor por chunk
    # numa unica requisicao - timeout generoso.
    with httpx.Client(base_url=stack.backend_url, timeout=300.0) as client:
        yield client


@pytest.fixture(scope="session")
def corpus_version() -> str:
    return case1_manifest_corpus_version()


def ingest_case1(backend: httpx.Client, corpus_version: str) -> dict:
    response = backend.post(
        "/v1/ingestions", json={"corpus": "case1-real", "corpus_version": corpus_version}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(scope="session")
def ingested(backend: httpx.Client, corpus_version: str) -> dict:
    """Caso 1 ingerido pelo backend (dono do catalogo) uma vez por sessao."""
    return ingest_case1(backend, corpus_version)
