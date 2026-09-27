"""Contrato do endpoint publico de ingestao do corpus fixture demo.

Seam testado: POST /v1/ingestions. Isola o ai via dependency override
de get_ai_client (fake deterministico, nunca HTTP real - o ai real nao
sobe nestes testes) e roda contra um Postgres real de teste (container
Docker, ver tests/conftest.py) - SQLite em memoria mascararia o
dialeto Postgres usado pelo upsert do catalogo.
"""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import IndexDocumentPayload, IndexReport, get_ai_client
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.fixtures.case1_loader import CASE1_REAL_CORPUS_VERSION, load_case1_real_corpus
from app.fixtures.loader import load_demo_corpus
from app.main import create_app
from app.models import DocumentFamily, DocumentVersion
from app.routes.ingestions import run_ingestion


class _FakeAiClient:
    """Fake deterministico do AiClient - sem HTTP real, seguindo o
    mesmo padrao de dependency override do teste de health (Ticket 1).
    """

    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        return [
            IndexReport(
                document_version=doc.document_version,
                extracted_text_locator=f"/data/documents/{doc.document_version}/extracted.txt",
                chunks_indexed=len([b for b in doc.text.split("\n\n") if b.strip()]),
                model_version="fixture-demo",
            )
            for doc in documents
        ]


def _client(database_url: str) -> tuple[TestClient, sessionmaker[Session]]:
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

    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeAiClient()
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app), session_factory


def test_ingestion_populates_catalog_with_exact_fixture_values(database_url: str) -> None:
    client, session_factory = _client(database_url)
    corpus = load_demo_corpus()
    expected_family_ids = {doc.family_id for doc in corpus.documents}

    response = client.post("/v1/ingestions")

    assert response.status_code == 200
    body = response.json()
    assert body["families_count"] == len(expected_family_ids)
    assert body["versions_count"] == len(corpus.documents)
    assert body["ingestion_job_id"]

    with session_factory() as session:
        families = {f.family_id for f in session.scalars(select(DocumentFamily))}
        versions = {v.document_version: v for v in session.scalars(select(DocumentVersion))}

    assert families == expected_family_ids
    assert set(versions) == {doc.document_version for doc in corpus.documents}
    for doc in corpus.documents:
        version = versions[doc.document_version]
        assert version.family_id == doc.family_id
        assert version.version_date == doc.version_date
        assert version.version_date_source == doc.version_date_source
        assert version.document_type == doc.document_type
        assert version.processo_numero == doc.processo_numero
        assert version.corpus_version == corpus.corpus_version
        assert version.model_version == "fixture-demo"
        expected_locator = f"/data/documents/{doc.document_version}/extracted.txt"
        assert version.extracted_text_locator == expected_locator


def test_reingesting_same_fixture_does_not_duplicate_catalog_rows(database_url: str) -> None:
    client, session_factory = _client(database_url)
    corpus = load_demo_corpus()
    expected_family_ids = {doc.family_id for doc in corpus.documents}

    first_response = client.post("/v1/ingestions")
    second_response = client.post("/v1/ingestions")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    # ingestion_job_id e por chamada, nao por linha do catalogo - cada POST gera um novo.
    assert first_response.json()["ingestion_job_id"] != second_response.json()["ingestion_job_id"]

    second_body = second_response.json()
    assert second_body["families_count"] == len(expected_family_ids)
    assert second_body["versions_count"] == len(corpus.documents)

    with session_factory() as session:
        family_count = session.scalar(select(func.count()).select_from(DocumentFamily))
        version_count = session.scalar(select(func.count()).select_from(DocumentVersion))

    assert family_count == len(expected_family_ids)
    assert version_count == len(corpus.documents)


def test_family_with_multiple_versions_and_shared_processo_are_ingested(
    database_url: str,
) -> None:
    """Cobre os dois cenarios exigidos pela issue #18: uma familia com
    2+ versoes e um conjunto de documentos com o mesmo processo_numero
    em familias distintas.
    """
    client, session_factory = _client(database_url)
    client.post("/v1/ingestions")

    with session_factory() as session:
        auto_versions = session.scalars(
            select(DocumentVersion).where(DocumentVersion.family_id == "fam-auto-0007")
        ).all()
        same_processo = session.scalars(
            select(DocumentVersion).where(
                DocumentVersion.processo_numero == "48500.001234/2024-11"
            )
        ).all()

    assert len(auto_versions) >= 2
    assert len({v.family_id for v in same_processo}) >= 2


class _RealModeAiClient:
    """Fake que devolve total_input_tokens (issue #73, AC "custo de
    embeddings"), como o ai real faz em EMBEDDER=bedrock."""

    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        return [
            IndexReport(
                document_version=doc.document_version,
                extracted_text_locator=f"/data/documents/{doc.document_version}/extracted.txt",
                chunks_indexed=1,
                model_version="amazon.titan-embed-text-v2-us-east-1-1024d-normalized",
                total_input_tokens=100,
            )
            for doc in documents
        ]


def test_run_ingestion_sums_total_input_tokens_across_documents(database_url: str) -> None:
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)
    corpus = load_demo_corpus()

    with session_factory() as session:
        result = run_ingestion(corpus, ai_client=_RealModeAiClient(), session=session)
        session.commit()

    assert result.total_input_tokens == 100 * len(corpus.documents)


def test_run_ingestion_total_input_tokens_is_none_in_fake_mode(database_url: str) -> None:
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)
    corpus = load_demo_corpus()

    with session_factory() as session:
        result = run_ingestion(corpus, ai_client=_FakeAiClient(), session=session)
        session.commit()

    assert result.total_input_tokens is None


# ---------------------------------------------------------------------------
# Corpus real do caso 1 via HTTP (issue #88)
# ---------------------------------------------------------------------------


class _RecordingAiClient(_FakeAiClient):
    def __init__(self) -> None:
        self.indexed: list[IndexDocumentPayload] = []

    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        self.indexed.extend(documents)
        return super().index(documents)


def _client_with(database_url: str, ai_client) -> tuple[TestClient, sessionmaker[Session]]:
    client, session_factory = _client(database_url)
    client.app.dependency_overrides[get_ai_client] = lambda: ai_client
    return client, session_factory


def test_ingestion_of_case1_real_corpus_sends_full_markdown_to_ai(database_url: str) -> None:
    ai_client = _RecordingAiClient()
    client, session_factory = _client_with(database_url, ai_client)
    corpus = load_case1_real_corpus()

    response = client.post("/v1/ingestions", json={"corpus": "case1-real"})

    assert response.status_code == 200
    assert response.json()["versions_count"] == len(corpus.documents) == 10
    sent = {doc.document_version: doc for doc in ai_client.indexed}
    for doc in corpus.documents:
        assert sent[doc.document_version].text == doc.text
        assert sent[doc.document_version].corpus_version == CASE1_REAL_CORPUS_VERSION

    with session_factory() as session:
        versions = list(session.scalars(select(DocumentVersion)))
    assert {v.corpus_version for v in versions} == {CASE1_REAL_CORPUS_VERSION}
    assert {v.document_version for v in versions} == set(sent)


def test_ingestion_of_case1_real_corpus_records_given_corpus_version(database_url: str) -> None:
    ai_client = _RecordingAiClient()
    client, session_factory = _client_with(database_url, ai_client)

    response = client.post(
        "/v1/ingestions", json={"corpus": "case1-real", "corpus_version": "manifest-hash-abc"}
    )

    assert response.status_code == 200
    assert {doc.corpus_version for doc in ai_client.indexed} == {"manifest-hash-abc"}
    with session_factory() as session:
        corpus_versions = set(session.scalars(select(DocumentVersion.corpus_version)))
    assert corpus_versions == {"manifest-hash-abc"}


def test_ingestion_rejects_unknown_corpus(database_url: str) -> None:
    client, _ = _client(database_url)

    response = client.post("/v1/ingestions", json={"corpus": "nao-existe"})

    assert response.status_code == 422


def test_case1_loader_honors_case_documents_dir(tmp_path, monkeypatch) -> None:
    """No container do backend o repositorio nao existe: o Markdown do caso 1
    chega montado em ``CASE_DOCUMENTS_DIR`` (docker-compose.yml)."""
    import shutil

    from app.fixtures import case1_loader

    shutil.copytree(case1_loader.default_case1_data_dir(), tmp_path / "case1")
    monkeypatch.setenv("CASE_DOCUMENTS_DIR", str(tmp_path / "case1"))

    assert case1_loader.default_case1_data_dir() == tmp_path / "case1"
    assert len(load_case1_real_corpus().documents) == 10
