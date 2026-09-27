"""URL do catalogo montada a partir de ``DB_*`` (issue #106).

Na AWS o ECS entrega host/porta/nome como variaveis e usuario/senha como
*secrets* vindos do segredo gerenciado pelo RDS; o Compose continua
passando ``DATABASE_URL`` pronta. ``DATABASE_URL`` tem precedencia.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy.engine import make_url

from app.config import get_settings

_DB_VARS = ("DATABASE_URL", "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")


@pytest.fixture(autouse=True)
def _clean_db_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in _DB_VARS:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _set_db_parts(monkeypatch: pytest.MonkeyPatch, password: str = "s3cret") -> None:
    monkeypatch.setenv("DB_HOST", "capiwatt.abc123.us-west-2.rds.amazonaws.com")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "capiwatt")
    monkeypatch.setenv("DB_PASSWORD", password)
    monkeypatch.setenv("DB_NAME", "capiwatt")


def test_database_url_is_built_from_db_parts_when_database_url_is_absent(monkeypatch):
    _set_db_parts(monkeypatch)

    assert get_settings().database_url == (
        "postgresql+psycopg://capiwatt:s3cret@"
        "capiwatt.abc123.us-west-2.rds.amazonaws.com:5432/capiwatt"
    )


def test_password_with_url_special_characters_survives_the_round_trip(monkeypatch):
    # O RDS gera senhas com pontuacao; '@', '/', ':' e '#' nao podem quebrar a URL.
    tricky = "p@ss/w:rd#1?%"
    _set_db_parts(monkeypatch, password=tricky)

    url = make_url(get_settings().database_url)

    assert url.password == tricky
    assert url.host == "capiwatt.abc123.us-west-2.rds.amazonaws.com"
    assert url.port == 5432
    assert url.database == "capiwatt"


def test_database_url_takes_precedence_over_db_parts(monkeypatch):
    _set_db_parts(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://compose:compose@postgres:5432/compose")

    assert get_settings().database_url == (
        "postgresql+psycopg://compose:compose@postgres:5432/compose"
    )


def test_without_database_url_nor_db_parts_keeps_the_compose_default():
    assert get_settings().database_url == (
        "postgresql+psycopg://capiwatt:capiwatt@postgres:5432/capiwatt"
    )
