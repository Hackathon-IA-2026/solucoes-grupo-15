"""Contrato de DELETE /internal/v1/documents/{document_version} (issue #98).

Operacao ``delete(document_version)`` do port VectorService
(requirements/contracts/backend-vector-service.md). Os testes observam o
efeito pela superficie publica do ``ai`` - a busca e a indexacao -, nunca
pelo estado interno do indice.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.embeddings import BedrockEmbedder
from app.main import create_app
from app.raw_vectors import RawVectorStore
from app.routes.index import (
    get_documents_root,
    get_embedder,
    get_raw_vector_store,
    get_vector_store,
)
from app.vector_store import InMemoryVectorStore
from tests.test_embeddings import FakeBedrockRuntimeClient

DOC_A = {
    "document_version": "docver-a",
    "text": "<!-- page:1 -->\ntexto do documento A\n",
    "family_id": "fam-a",
    "corpus_version": "corpus-v1",
}
DOC_B = {
    "document_version": "docver-b",
    "text": "<!-- page:1 -->\ntexto do documento B\n",
    "family_id": "fam-b",
    "corpus_version": "corpus-v1",
}


@pytest.fixture(autouse=True)
def _bedrock_mode(monkeypatch, request):
    if "no_bedrock_mode" in request.keywords:
        yield
        return
    monkeypatch.setenv("EMBEDDER", "bedrock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client(tmp_path: Path) -> TestClient:
    store = InMemoryVectorStore()
    app = create_app()
    app.dependency_overrides[get_documents_root] = lambda: tmp_path
    app.dependency_overrides[get_embedder] = lambda: BedrockEmbedder(FakeBedrockRuntimeClient())
    app.dependency_overrides[get_vector_store] = lambda: store
    app.dependency_overrides[get_raw_vector_store] = lambda: RawVectorStore(
        tmp_path / "_raw_vectors.jsonl"
    )
    return TestClient(app)


def _versions_found_by_search(client: TestClient) -> set[str]:
    response = client.post("/internal/v1/search", json={"query": "documento", "top_k": 100})
    assert response.status_code == 200
    return {hit["document_version"] for hit in response.json()["hits"]}


def test_delete_removes_only_that_version_from_search(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post("/internal/v1/index", json={"documents": [DOC_A, DOC_B]})
    assert _versions_found_by_search(client) == {"docver-a", "docver-b"}

    response = client.delete("/internal/v1/documents/docver-a")

    assert response.status_code == 200
    assert response.json() == {
        "document_version": "docver-a",
        "model_version": REAL_MODEL_VERSION,
        "chunks_deleted": 1,
    }
    assert _versions_found_by_search(client) == {"docver-b"}


def test_index_after_delete_puts_the_version_back(tmp_path: Path) -> None:
    """O cache de idempotencia de ``index`` nao pode devolver o relatorio
    antigo de uma versao apagada: indexar de novo tem que regravar os chunks."""
    client = _client(tmp_path)
    client.post("/internal/v1/index", json={"documents": [DOC_A, DOC_B]})
    client.delete("/internal/v1/documents/docver-a")

    response = client.post("/internal/v1/index", json={"documents": [DOC_A]})

    assert response.status_code == 200
    assert _versions_found_by_search(client) == {"docver-a", "docver-b"}


def test_delete_is_idempotent_and_unknown_version_is_not_an_error(tmp_path: Path) -> None:
    """Decisao conservadora (issue #98): apagar de novo, ou apagar uma versao
    que nunca foi indexada, responde 200 com ``chunks_deleted: 0`` - um
    retry do backend apos timeout nunca vira erro. O 0 diz ao chamador que
    nada havia no indice."""
    client = _client(tmp_path)
    client.post("/internal/v1/index", json={"documents": [DOC_A, DOC_B]})
    client.delete("/internal/v1/documents/docver-a")

    again = client.delete("/internal/v1/documents/docver-a")
    unknown = client.delete("/internal/v1/documents/nunca-indexada")

    assert again.status_code == 200
    assert again.json()["chunks_deleted"] == 0
    assert unknown.status_code == 200
    assert unknown.json() == {
        "document_version": "nunca-indexada",
        "model_version": REAL_MODEL_VERSION,
        "chunks_deleted": 0,
    }
    assert _versions_found_by_search(client) == {"docver-b"}


def test_delete_tombstones_raw_vectors_so_offline_reindex_does_not_revive_it(
    tmp_path: Path,
) -> None:
    """Os vetores brutos (issue #73, I7) alimentam o reindex offline
    (tools/case1_recall/reindex_from_raw_vectors.py). Se a versao apagada
    continuasse viva no replay deles, o reindex offline a ressuscitaria no
    indice. O arquivo e append-only: o delete grava um tombstone, as linhas
    antigas continuam no disco."""
    client = _client(tmp_path)
    client.post("/internal/v1/index", json={"documents": [DOC_A, DOC_B]})

    client.delete("/internal/v1/documents/docver-a")

    raw = RawVectorStore(tmp_path / "_raw_vectors.jsonl")
    assert {c.document_version for c in raw.load_all()} == {"docver-b"}
    assert '"document_version": "docver-a"' in raw_text(tmp_path)


def raw_text(tmp_path: Path) -> str:
    return (tmp_path / "_raw_vectors.jsonl").read_text(encoding="utf-8")


def test_delete_keeps_the_extracted_text_file(tmp_path: Path) -> None:
    """Decisao conservadora (issue #98): o texto em ``extracted_text_locator``
    fica. Ele esta registrado no catalogo do backend (dono do ciclo de vida
    da versao) e e o que a pagina do documento le; ``delete`` so mexe no
    derivado (indice + vetores brutos)."""
    client = _client(tmp_path)
    [report] = client.post("/internal/v1/index", json={"documents": [DOC_A]}).json()["reports"]

    client.delete("/internal/v1/documents/docver-a")

    assert Path(report["extracted_text_locator"]).read_text(encoding="utf-8") == DOC_A["text"]


@pytest.mark.no_bedrock_mode
def test_delete_in_fixture_mode_forgets_the_version(tmp_path: Path) -> None:
    """Modo fixture: nao ha indice vetorial (a busca e declarativa), entao o
    "indice" e o cache de relatorios de ``index``. ``delete`` esquece a
    versao - ``chunks_deleted`` = blocos que ela tinha - e um ``index``
    seguinte reprocessa o texto novo em vez de devolver o relatorio antigo."""
    app = create_app()
    app.dependency_overrides[get_documents_root] = lambda: tmp_path
    client = TestClient(app)
    client.post(
        "/internal/v1/index",
        json={"documents": [{"document_version": "docver-1", "text": "um\n\ndois"}]},
    )

    response = client.delete("/internal/v1/documents/docver-1")
    again = client.delete("/internal/v1/documents/docver-1")
    [report] = client.post(
        "/internal/v1/index",
        json={"documents": [{"document_version": "docver-1", "text": "um\n\ndois\n\ntres"}]},
    ).json()["reports"]

    assert response.status_code == 200
    assert response.json() == {
        "document_version": "docver-1",
        "model_version": "fixture-demo",
        "chunks_deleted": 2,
    }
    assert again.json()["chunks_deleted"] == 0
    assert report["chunks_indexed"] == 3
