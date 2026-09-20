"""Fixture de Postgres real para os testes de integracao do catalogo.

Decisao de teste (issue #16, Testing Decisions, seam 2 / issue #18):
Postgres real via container de teste, nunca SQLite em memoria - evita
mascarar comportamento especifico do dialeto Postgres usado pelo
upsert do catalogo (session.get por PK + insert/update).

Sobe um container ``postgres:16-alpine`` dedicado (porta efemera do
host, nao colide com o Postgres do docker-compose.yml), aguarda ficar
pronto e derruba no fim da sessao de testes. Requer o binario `docker`
disponivel; os testes que dependem desta fixture sao pulados (skip) se
o Docker nao estiver acessivel, em vez de falhar a suite inteira.
"""

import subprocess
import time
import uuid
from collections.abc import Iterator

import psycopg
import pytest

_IMAGE = "postgres:16-alpine"
_USER = "capiwatt_test"
_PASSWORD = "capiwatt_test"
_DB = "capiwatt_test"


def _docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "info"], check=True, capture_output=True, timeout=10
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return True


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[str]:
    if not _docker_available():
        pytest.skip("Docker indisponivel - necessario para o Postgres de teste (seam 2)")

    container_name = f"capiwatt-backend-test-pg-{uuid.uuid4().hex[:8]}"
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "-e",
            f"POSTGRES_USER={_USER}",
            "-e",
            f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e",
            f"POSTGRES_DB={_DB}",
            "-p",
            "127.0.0.1::5432",
            _IMAGE,
        ],
        check=True,
        capture_output=True,
    )
    try:
        port = _published_port(container_name)
        _wait_ready(port)
        yield f"postgresql+psycopg://{_USER}:{_PASSWORD}@127.0.0.1:{port}/{_DB}"
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


def _published_port(container_name: str) -> str:
    result = subprocess.run(
        ["docker", "port", container_name, "5432/tcp"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split(":")[-1]


def _wait_ready(port: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(
                f"host=127.0.0.1 port={port} user={_USER} password={_PASSWORD} dbname={_DB}",
                connect_timeout=2,
            ):
                return
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Postgres de teste nao ficou pronto a tempo: {last_error}")


@pytest.fixture
def database_url(postgres_container: str) -> str:
    return postgres_container
