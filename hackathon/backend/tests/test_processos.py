"""Contratos do catalogo e da pagina de processo (issues #21 e #36).

Seam testado: GET /v1/processos/{processo_id}. Roda contra um Postgres
real de teste (container Docker, ver tests/conftest.py), populado via
``run_ingestion`` (corpus + fixture de relacoes) antes de cada teste.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import IndexDocumentPayload, IndexReport, get_ai_client
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.fixtures.loader import load_demo_corpus
from app.fixtures.relations_loader import load_demo_relations
from app.main import create_app
from app.routes.ingestions import run_ingestion

PROCESSO_ID = "48500.001234/2024-11"


class _SeedAiClient:
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


def _client(database_url: str) -> TestClient:
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

    _seed_catalog(session_factory)

    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _SeedAiClient()
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app)


def _seed_catalog(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        run_ingestion(
            load_demo_corpus(),
            ai_client=_SeedAiClient(),
            session=session,
            relations=load_demo_relations(),
        )
        session.commit()


def test_processo_lists_pieces_ordered_by_face_date(database_url: str) -> None:
    client = _client(database_url)

    response = client.get(f"/v1/processos/{PROCESSO_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["processo_id"] == PROCESSO_ID

    pieces = body["pieces"]
    # Ordenado pela data representativa (face de cada familia): defesa
    # (2024-03-20) < auto v2/face (2024-04-18, nao a v1 de 2024-03-04) <
    # decisao (2024-05-02).
    assert [p["family_id"] for p in pieces] == [
        "fam-defesa-0007",
        "fam-auto-0007",
        "fam-decisao-0007",
    ]
    assert [p["version_date"] for p in pieces] == [
        "2024-03-20",
        "2024-04-18",
        "2024-05-02",
    ]


def test_processos_lists_catalog_summary_from_representative_faces(database_url: str) -> None:
    client = _client(database_url)

    response = client.get("/v1/processos")

    assert response.status_code == 200
    assert response.json() == [
        {
            "processo_id": PROCESSO_ID,
            "latest_movement_at": "2024-05-02",
            "latest_document_type": "decisao",
            "latest_document_id": "decisao-0007",
            "pieces_count": 3,
            "document_types": ["auto_de_infracao", "decisao", "peticao"],
        }
    ]


def test_processos_does_not_list_family_without_process_number(database_url: str) -> None:
    client = _client(database_url)

    response = client.get("/v1/processos")

    assert response.status_code == 200
    assert all(item["processo_id"] != "fam-norma-1000" for item in response.json())


def test_processo_piece_includes_document_type_and_document_id(database_url: str) -> None:
    client = _client(database_url)

    response = client.get(f"/v1/processos/{PROCESSO_ID}")

    pieces = {p["family_id"]: p for p in response.json()["pieces"]}
    assert pieces["fam-auto-0007"]["document_type"] == "auto_de_infracao"
    assert pieces["fam-auto-0007"]["document_id"] == "auto-0007"


def test_processo_includes_responde_a_chain_between_its_pieces(database_url: str) -> None:
    client = _client(database_url)

    response = client.get(f"/v1/processos/{PROCESSO_ID}")

    responde_a = response.json()["responde_a"]
    assert len(responde_a) == 1
    assert responde_a[0]["source_family_id"] == "fam-defesa-0007"
    assert responde_a[0]["target_family_id"] == "fam-auto-0007"
    assert responde_a[0]["evidence"]["document_version"] == "docver-defesa-0007-v1"


def test_processo_without_pieces_returns_404(database_url: str) -> None:
    client = _client(database_url)

    response = client.get("/v1/processos/00000.000000/9999-00")

    assert response.status_code == 404


def test_family_without_processo_does_not_appear_as_a_processo(database_url: str) -> None:
    """fam-norma-1000 nao tem processo_numero - nao deve ser tratavel
    como processo nem gerar entrada por engano."""
    client = _client(database_url)

    response = client.get("/v1/processos/fam-norma-1000")

    assert response.status_code == 404
