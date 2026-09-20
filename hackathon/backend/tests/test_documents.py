"""Contrato do endpoint publico de leitura de documento (TB1 Ticket 4, issue #20).

Seam testado: GET /v1/documents/{family_id}. Roda contra um Postgres
real de teste (container Docker, ver tests/conftest.py), populado via
``run_ingestion`` (mesmo padrao de test_search.py/test_ingestions.py) -
o fake de ``AiClient.index`` usado para popular escreve arquivos reais
num diretorio temporario, para que a leitura de
``extracted_text_locator`` (filesystem direto, sem HTTP) tenha o que
ler.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import IndexDocumentPayload, IndexReport, get_ai_client
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.fixtures.loader import load_demo_corpus
from app.main import create_app
from app.routes.ingestions import run_ingestion


class _SeedAiClient:
    """Fake deterministico que grava arquivos reais em ``root`` -
    necessario aqui porque, ao contrario de test_search.py/test_ingestions.py,
    GET /v1/documents le o texto direto do filesystem (extracted_text_locator).
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        reports = []
        for doc in documents:
            version_dir = self._root / doc.document_version
            version_dir.mkdir(parents=True, exist_ok=True)
            extracted_path = version_dir / "extracted.txt"
            extracted_path.write_text(doc.text, encoding="utf-8")
            reports.append(
                IndexReport(
                    document_version=doc.document_version,
                    extracted_text_locator=str(extracted_path),
                    chunks_indexed=1,
                    model_version="fixture-demo",
                )
            )
        return reports


def _client(database_url: str, documents_root: Path) -> TestClient:
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)

    def _override_session():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    _seed_catalog(session_factory, documents_root)

    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _SeedAiClient(documents_root)
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app)


def _seed_catalog(session_factory: sessionmaker[Session], documents_root: Path) -> None:
    with session_factory() as session:
        run_ingestion(
            load_demo_corpus(), ai_client=_SeedAiClient(documents_root), session=session
        )
        session.commit()


@pytest.fixture
def documents_root(tmp_path: Path) -> Path:
    return tmp_path / "documents"


def test_get_document_without_version_returns_the_latest_version(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)

    response = client.get("/v1/documents/fam-auto-0007")

    assert response.status_code == 200
    body = response.json()
    assert body["family_id"] == "fam-auto-0007"
    assert body["document_id"] == "auto-0007"
    assert body["selected_version"]["document_version"] == "docver-auto-0007-v2"
    assert body["selected_version"]["version_date"] == "2024-04-18"
    assert "versao retificada" in body["selected_version"]["text"]


def test_get_document_with_older_version_returns_that_specific_version(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)

    response = client.get(
        "/v1/documents/fam-auto-0007", params={"version": "docver-auto-0007-v1"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_version"]["document_version"] == "docver-auto-0007-v1"
    assert body["selected_version"]["version_date"] == "2024-03-04"
    assert "versao retificada" not in body["selected_version"]["text"]


def test_get_document_with_version_not_belonging_to_family_falls_back_to_latest(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)

    response = client.get(
        "/v1/documents/fam-auto-0007", params={"version": "docver-norma-1000-v1"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_version"]["document_version"] == "docver-auto-0007-v2"


def test_get_document_lists_all_versions_ordered_most_recent_first(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)

    response = client.get("/v1/documents/fam-auto-0007")

    versions = response.json()["versions"]
    assert [v["document_version"] for v in versions] == [
        "docver-auto-0007-v2",
        "docver-auto-0007-v1",
    ]
    assert [v["version_date"] for v in versions] == ["2024-04-18", "2024-03-04"]


def test_get_document_includes_document_id_and_processo_numero(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)

    response = client.get("/v1/documents/fam-auto-0007")

    body = response.json()
    assert body["document_id"] == "auto-0007"
    assert body["document_type"] == "auto_de_infracao"
    assert body["processo_numero"] == "48500.001234/2024-11"


def test_get_document_without_processo_returns_null(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)

    response = client.get("/v1/documents/fam-norma-1000")

    assert response.status_code == 200
    assert response.json()["processo_numero"] is None


def test_get_document_text_matches_the_file_written_by_ai_index(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)
    corpus = load_demo_corpus()
    expected_text = next(
        doc.text for doc in corpus.documents if doc.document_version == "docver-auto-0007-v2"
    )

    response = client.get("/v1/documents/fam-auto-0007")

    assert response.json()["selected_version"]["text"] == expected_text


def test_get_document_returns_404_for_unknown_family(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)

    response = client.get("/v1/documents/fam-inexistente")

    assert response.status_code == 404


def test_get_document_returns_404_when_extracted_text_file_is_missing(
    database_url: str, documents_root: Path
) -> None:
    client = _client(database_url, documents_root)
    missing_path = documents_root / "docver-auto-0007-v2" / "extracted.txt"
    missing_path.unlink()

    response = client.get("/v1/documents/fam-auto-0007")

    assert response.status_code == 404
