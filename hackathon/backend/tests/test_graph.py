"""Contrato do endpoint publico de grafo de relacoes (TB1 Ticket 5, issue #21).

Seam testado: GET /v1/documents/{node_id}/graph. Roda contra um
Postgres real de teste (container Docker, ver tests/conftest.py),
populado via ``run_ingestion`` (corpus + fixture de relacoes) antes de
cada teste, mesmo padrao dos demais testes de rota deste modulo.
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
    """Fake deterministico usado so para popular o catalogo via
    run_ingestion antes de cada teste (mesmo padrao de test_ingestions.py).
    """

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


def test_graph_of_a_piece_family_includes_outgoing_and_incoming_edges(
    database_url: str,
) -> None:
    client = _client(database_url)

    response = client.get("/v1/documents/fam-auto-0007/graph")

    assert response.status_code == 200
    body = response.json()
    assert body["node_id"] == "fam-auto-0007"
    assert body["node_kind"] == "family"

    edges_by_type = {edge["type"]: edge for edge in body["edges"]}

    # aresta de saida: fam-auto-0007 pertence ao processo
    pertence = edges_by_type["pertence_ao_processo"]
    assert pertence["neighbor_id"] == PROCESSO_ID
    assert pertence["neighbor_kind"] == "processo"
    assert pertence["origin"] == "explicit"
    assert pertence["status"] == "confirmed"
    assert pertence["evidence"] is None

    # aresta de entrada: fam-defesa-0007 responde_a fam-auto-0007
    responde_a = edges_by_type["responde_a"]
    assert responde_a["neighbor_id"] == "fam-defesa-0007"
    assert responde_a["neighbor_kind"] == "family"
    assert responde_a["evidence"]["document_version"] == "docver-defesa-0007-v1"

    # aresta de entrada: fam-decisao-0007 referencia fam-auto-0007
    referencia = edges_by_type["referencia"]
    assert referencia["neighbor_id"] == "fam-decisao-0007"
    assert referencia["neighbor_kind"] == "family"
    assert referencia["evidence"]["document_version"] == "docver-decisao-0007-v1"

    assert len(body["edges"]) == 3


def test_graph_of_norma_family_shows_regula_edge_to_decisao(database_url: str) -> None:
    client = _client(database_url)

    response = client.get("/v1/documents/fam-norma-1000/graph")

    assert response.status_code == 200
    [edge] = response.json()["edges"]
    assert edge["type"] == "regula"
    assert edge["neighbor_id"] == "fam-decisao-0007"
    assert edge["neighbor_kind"] == "family"
    assert edge["origin"] == "explicit"
    assert edge["status"] == "confirmed"
    assert edge["evidence"]["document_version"] == "docver-decisao-0007-v1"


def test_graph_of_a_processo_node_lists_the_three_pertence_edges(database_url: str) -> None:
    client = _client(database_url)

    response = client.get(f"/v1/documents/{PROCESSO_ID}/graph")

    assert response.status_code == 200
    body = response.json()
    assert body["node_kind"] == "processo"
    neighbor_ids = {edge["neighbor_id"] for edge in body["edges"]}
    assert neighbor_ids == {"fam-auto-0007", "fam-defesa-0007", "fam-decisao-0007"}
    assert all(edge["type"] == "pertence_ao_processo" for edge in body["edges"])
    assert all(edge["neighbor_kind"] == "family" for edge in body["edges"])


def test_graph_returns_404_for_a_node_that_does_not_exist(database_url: str) -> None:
    client = _client(database_url)

    response = client.get("/v1/documents/fam-inexistente/graph")

    assert response.status_code == 404


def test_graph_of_a_family_without_relations_returns_empty_edges(database_url: str) -> None:
    """fam-defesa-0007 existe no catalogo mas nao tem nenhuma aresta
    testada separadamente aqui - usamos uma familia com pertence_ao_processo
    para garantir que ausencia de OUTRAS arestas nao aparece."""
    client = _client(database_url)

    response = client.get("/v1/documents/fam-decisao-0007/graph")

    assert response.status_code == 200
    body = response.json()
    types = {edge["type"] for edge in body["edges"]}
    # decisao: pertence_ao_processo (saida), regula (entrada, da norma),
    # referencia (saida, para o auto)
    assert types == {"pertence_ao_processo", "regula", "referencia"}
