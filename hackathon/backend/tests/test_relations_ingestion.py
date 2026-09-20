"""Contrato de idempotencia da ingestao da fixture de relacoes (TB1
Ticket 5, issue #21, seam 3).

Reingerir POST /v1/ingestions duas vezes nao deve duplicar linhas de
``document_relations`` - upsert pela chave natural
``(source_id, source_kind, target_id, target_kind, type)``. Mesmo
padrao de isolamento dos demais testes deste modulo: Postgres real de
teste (tests/conftest.py) e ``AiClient`` fake via dependency override.
"""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import IndexDocumentPayload, IndexReport, get_ai_client
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.fixtures.relations_loader import load_demo_relations
from app.main import create_app
from app.models import DocumentRelation


class _FakeAiClient:
    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        return [
            IndexReport(
                document_version=doc.document_version,
                extracted_text_locator=f"/data/documents/{doc.document_version}/extracted.txt",
                chunks_indexed=1,
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


def test_ingestion_populates_document_relations_with_exact_fixture_values(
    database_url: str,
) -> None:
    client, session_factory = _client(database_url)
    relations = load_demo_relations()

    response = client.post("/v1/ingestions")

    assert response.status_code == 200
    assert response.json()["relations_count"] == len(relations.relations)

    with session_factory() as session:
        rows = session.scalars(select(DocumentRelation)).all()

    assert len(rows) == len(relations.relations)
    for row in rows:
        assert row.origin == "explicit"
        assert row.status == "confirmed"


def test_reingesting_same_fixture_does_not_duplicate_relations_rows(
    database_url: str,
) -> None:
    client, session_factory = _client(database_url)
    relations = load_demo_relations()

    first = client.post("/v1/ingestions")
    second = client.post("/v1/ingestions")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["relations_count"] == len(relations.relations)

    with session_factory() as session:
        count = session.scalar(select(func.count()).select_from(DocumentRelation))

    assert count == len(relations.relations)


def test_reingesting_same_fixture_keeps_evidence_intact(database_url: str) -> None:
    client, session_factory = _client(database_url)

    client.post("/v1/ingestions")
    client.post("/v1/ingestions")

    with session_factory() as session:
        row = session.scalar(
            select(DocumentRelation).where(
                DocumentRelation.source_id == "fam-defesa-0007",
                DocumentRelation.type == "responde_a",
            )
        )

    assert row is not None
    assert row.evidence_document_version == "docver-defesa-0007-v1"
    assert row.evidence_locator is not None
