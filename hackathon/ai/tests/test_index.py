"""Contrato do endpoint interno de indexacao (adapter demo) do modulo ai.

Seam testado: POST /internal/v1/index, chamado pelo backend via HTTP
(nunca importando o modulo ai diretamente). Roda em processo, sem
Docker: a raiz do volume de documentos e sobrescrita via
dependency_overrides para um diretorio temporario do pytest.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.routes.index import get_documents_root


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_documents_root] = lambda: tmp_path
    return TestClient(app)


def test_index_writes_extracted_text_and_counts_chunks(client: TestClient) -> None:
    document = {"document_version": "docver-1", "text": "paragrafo um\n\nparagrafo dois"}
    response = client.post("/internal/v1/index", json={"documents": [document]})

    assert response.status_code == 200
    [report] = response.json()["reports"]
    assert report["document_version"] == "docver-1"
    assert report["chunks_indexed"] == 2
    assert report["model_version"] == "fixture-demo"

    extracted = Path(report["extracted_text_locator"])
    assert extracted.read_text(encoding="utf-8") == "paragrafo um\n\nparagrafo dois"


def test_index_handles_multiple_documents_independently(client: TestClient) -> None:
    response = client.post(
        "/internal/v1/index",
        json={
            "documents": [
                {"document_version": "docver-a", "text": "x\n\ny\n\nz"},
                {"document_version": "docver-b", "text": "bloco unico"},
            ]
        },
    )

    reports = response.json()["reports"]
    chunks_by_version = {r["document_version"]: r["chunks_indexed"] for r in reports}
    assert chunks_by_version == {"docver-a": 3, "docver-b": 1}


def test_index_is_idempotent_for_same_document_version_and_model_version(
    client: TestClient,
) -> None:
    payload = {"documents": [{"document_version": "docver-2", "text": "bloco unico"}]}

    first = client.post("/internal/v1/index", json=payload).json()["reports"][0]
    extracted_path = Path(first["extracted_text_locator"])
    original_mtime = extracted_path.stat().st_mtime_ns

    second = client.post("/internal/v1/index", json=payload).json()["reports"][0]

    assert second == first
    assert extracted_path.stat().st_mtime_ns == original_mtime


def test_reindexing_with_different_text_after_idempotent_hit_is_ignored(
    client: TestClient,
) -> None:
    """Mesmo (document_version, model_version): mesmo texto novo NAO reescreve."""
    client.post(
        "/internal/v1/index",
        json={"documents": [{"document_version": "docver-3", "text": "texto original"}]},
    )

    document = {"document_version": "docver-3", "text": "texto totalmente diferente"}
    response = client.post("/internal/v1/index", json={"documents": [document]})

    report = response.json()["reports"][0]
    extracted_path = Path(report["extracted_text_locator"])
    assert extracted_path.read_text(encoding="utf-8") == "texto original"
