"""Arestas vindas do ai viram ``document_relations`` visiveis no grafo (issue #92).

Seams testados: POST /v1/ingestions (corpus ``case1-real``) seguido de
GET /v1/documents/{node_id}/graph. O ai e um dublê (dependency override
de ``get_ai_client``) que devolve candidatos roteirizados:
``references[]`` no ``IndexReport`` e ``similar_families``. Postgres real
de teste (tests/conftest.py).

Regras sob teste (d14-data-operations-modeling, i10, limiares da #74):

- vizinho com ``limiar_relacao (0.80) <= score < limiar_fusao (0.97)`` ->
  aresta ``similar_a`` ``origin=similarity``/``status=suggested`` com score,
  uma so por par (a vizinhanca e simetrica);
- ``score >= limiar_fusao`` e candidato a fusao, nunca ``similar_a``;
  ``score < limiar_relacao`` e descartado;
- referencia "Auto de Infração nº N/AAAA[-SIGLA]" resolvida pela chave
  tipo + identificador oficial contra o ``document_id`` do catalogo ->
  aresta ``referencia`` ``origin=explicit``/``status=confirmed`` com
  evidencia (versao + localizador).
"""

from fastapi.testclient import TestClient

from app.clients.ai_client import (
    AiReference,
    AiSimilarFamily,
    IndexDocumentPayload,
    IndexReport,
    get_ai_client,
)
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.main import create_app


class _ScriptedAiClient:
    def __init__(
        self,
        references: dict[str, list[AiReference]] | None = None,
        similar: dict[str, list[tuple[str, float]]] | None = None,
    ) -> None:
        self._references = references or {}
        self._similar = similar or {}
        self.similar_calls: list[tuple[str, int]] = []

    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        return [
            IndexReport(
                document_version=doc.document_version,
                extracted_text_locator=f"/data/documents/{doc.document_version}/extracted.txt",
                chunks_indexed=1,
                model_version="amazon.titan-embed-text-v2-us-east-1-1024d-normalized",
                references=self._references.get(doc.document_version, []),
            )
            for doc in documents
        ]

    def similar_families(self, family_id: str, top_k: int) -> list[AiSimilarFamily]:
        self.similar_calls.append((family_id, top_k))
        return [
            AiSimilarFamily(family_id=fid, score=score)
            for fid, score in self._similar.get(family_id, [])
        ]


def _client(database_url: str, ai_client: _ScriptedAiClient) -> TestClient:
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
    app.dependency_overrides[get_ai_client] = lambda: ai_client
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app)


def _ingest(client: TestClient) -> dict:
    response = client.post("/v1/ingestions", json={"corpus": "case1-real"})
    assert response.status_code == 200, response.text
    return response.json()


def _edges(client: TestClient, node_id: str) -> list[dict]:
    response = client.get(f"/v1/documents/{node_id}/graph")
    assert response.status_code == 200, response.text
    return response.json()["edges"]


def _ref(identifier: str, locator: str) -> AiReference:
    return AiReference(identifier_raw=identifier, relation_type=None, locator=locator)


# ---------------------------------------------------------------------------
# similar_families -> similar_a
# ---------------------------------------------------------------------------


def test_similar_candidate_between_thresholds_becomes_suggested_similar_a_edge(
    database_url: str,
) -> None:
    ai = _ScriptedAiClient(similar={"case1-cemig-auto": [("case1-enel-auto", 0.8368)]})
    client = _client(database_url, ai)

    _ingest(client)

    [edge] = _edges(client, "case1-cemig-auto")
    assert edge == {
        "type": "similar_a",
        "origin": "similarity",
        "status": "suggested",
        "neighbor_id": "case1-enel-auto",
        "neighbor_kind": "family",
        "evidence": None,
        "score": 0.8368,
    }
    # visivel dos dois lados
    [reverse] = _edges(client, "case1-enel-auto")
    assert reverse["neighbor_id"] == "case1-cemig-auto"


def test_ingestion_asks_ai_for_top_3_neighbors_of_every_family(database_url: str) -> None:
    ai = _ScriptedAiClient()
    client = _client(database_url, ai)

    _ingest(client)

    assert sorted(ai.similar_calls) == sorted(
        (fid, 3)
        for fid in [
            "case1-cemig-auto",
            "case1-cemig-recurso",
            "case1-cemig-voto",
            "case1-coelba-auto",
            "case1-coelba-complemento",
            "case1-coelba-recurso",
            "case1-coelba-voto",
            "case1-enel-auto",
            "case1-enel-recurso",
            "case1-enel-voto",
        ]
    )


def test_symmetric_neighborhood_is_recorded_once(database_url: str) -> None:
    ai = _ScriptedAiClient(
        similar={
            "case1-cemig-recurso": [("case1-cemig-voto", 0.9278)],
            "case1-cemig-voto": [("case1-cemig-recurso", 0.9278)],
        }
    )
    client = _client(database_url, ai)

    body = _ingest(client)

    assert len(_edges(client, "case1-cemig-voto")) == 1
    assert body["relations_count"] == 1


def test_thresholds_calibrated_in_issue_74_decide_which_candidates_become_edges(
    database_url: str,
) -> None:
    ai = _ScriptedAiClient(
        similar={
            "case1-coelba-auto": [
                ("case1-coelba-voto", 0.97),  # limiar_fusao: fusao, nunca similar_a
                ("case1-coelba-recurso", 0.80),  # limiar_relacao: entra
                ("case1-coelba-complemento", 0.7999),  # abaixo: descartado
            ]
        }
    )
    client = _client(database_url, ai)

    _ingest(client)

    edges = _edges(client, "case1-coelba-auto")
    assert [(e["type"], e["neighbor_id"], e["score"]) for e in edges] == [
        ("similar_a", "case1-coelba-recurso", 0.80)
    ]


def test_neighbor_outside_the_catalog_is_ignored(database_url: str) -> None:
    ai = _ScriptedAiClient(similar={"case1-enel-auto": [("fam-fora-do-catalogo", 0.9)]})
    client = _client(database_url, ai)

    _ingest(client)

    assert _edges(client, "case1-enel-auto") == []


def test_reingestion_does_not_duplicate_ai_edges(database_url: str) -> None:
    ai = _ScriptedAiClient(
        references={
            "case1-enel-recurso-2019": [
                _ref("Auto de Infração nº 0032/2018-SFE", "case1-enel-recurso-2019#chunk-0001")
            ]
        },
        similar={"case1-enel-auto": [("case1-enel-voto", 0.9091)]},
    )
    client = _client(database_url, ai)

    _ingest(client)
    _ingest(client)

    assert len(_edges(client, "case1-enel-auto")) == 2


# ---------------------------------------------------------------------------
# references[] -> referencia
# ---------------------------------------------------------------------------


def test_reference_to_an_auto_de_infracao_in_the_catalog_becomes_explicit_edge(
    database_url: str,
) -> None:
    # document_id de case1-cemig-auto no catalogo: "AI 0017/2020-SFE"
    ai = _ScriptedAiClient(
        references={
            "case1-cemig-recurso-2020": [
                _ref("Auto de Infração nº 0017/2020-SFE", "case1-cemig-recurso-2020#chunk-0002"),
                # mesma peca citada sem zeros a esquerda nem sigla: mesma aresta
                _ref("Auto de Infração nº 17/2020", "case1-cemig-recurso-2020#chunk-0005"),
            ]
        }
    )
    client = _client(database_url, ai)

    body = _ingest(client)

    [edge] = _edges(client, "case1-cemig-recurso")
    assert edge == {
        "type": "referencia",
        "origin": "explicit",
        "status": "confirmed",
        "neighbor_id": "case1-cemig-auto",
        "neighbor_kind": "family",
        "evidence": {
            "document_version": "case1-cemig-recurso-2020",
            "locator": "case1-cemig-recurso-2020#chunk-0002",
        },
        "score": None,
    }
    assert body["relations_count"] == 1


def test_reference_resolves_against_a_document_id_that_embeds_the_auto_number(
    database_url: str,
) -> None:
    # document_id de case1-coelba-auto: "Exposicao de Motivos / AI 35/2025-SFT"
    ai = _ScriptedAiClient(
        references={
            "case1-coelba-complemento-2025": [
                _ref(
                    "Auto de Infração – AI – nº 0035/2025-SFT",
                    "case1-coelba-complemento-2025#chunk-0000",
                )
            ]
        }
    )
    client = _client(database_url, ai)

    _ingest(client)

    [edge] = _edges(client, "case1-coelba-complemento")
    assert (edge["type"], edge["neighbor_id"]) == ("referencia", "case1-coelba-auto")


def test_unresolved_self_and_mismatched_references_create_no_edge(database_url: str) -> None:
    ai = _ScriptedAiClient(
        references={
            "case1-cemig-recurso-2020": [
                # fora do corpus
                _ref("Auto de Infração nº 0001/2020-SFE", "case1-cemig-recurso-2020#chunk-0001"),
                # mesmo numero/ano, outra superintendencia
                _ref("Auto de Infração nº 0017/2020-SFT", "case1-cemig-recurso-2020#chunk-0001"),
            ],
            # o auto citando o proprio numero
            "case1-cemig-auto-2020": [
                _ref("Auto de Infração nº 0017/2020-SFE", "case1-cemig-auto-2020#chunk-0000")
            ],
        }
    )
    client = _client(database_url, ai)

    body = _ingest(client)

    assert _edges(client, "case1-cemig-auto") == []
    assert body["relations_count"] == 0
