"""Contrato do endpoint interno de busca (adapter demo) do modulo ai.

Seam testado: POST /internal/v1/search, chamado pelo backend via HTTP
(nunca importando o modulo ai diretamente). Roda em processo, sem
Docker, contra o fixture real embarcado no modulo
(app/fixtures/search_fixtures.json) - o proprio teste tambem serve de
documentacao executavel para as consultas de exemplo declaradas.
"""

from fastapi.testclient import TestClient

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_search_returns_declared_hit_matching_the_oldest_version_of_a_family() -> None:
    """Prova o caso do AC2 da issue #19: o hit casado pode pertencer a
    uma versao mais antiga da familia (docver-auto-0007-v1, nao a mais
    recente docver-auto-0007-v2) - a regra "face = mais recente" e
    responsabilidade do backend, mas o ai precisa devolver o hit cru
    exatamente como declarado, sem promovê-lo para a versao mais nova.
    """
    client = _client()

    response = client.post(
        "/internal/v1/search",
        json={"query": "padrão de continuidade do fornecimento"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "fixture-demo"
    assert len(body["hits"]) == 1
    hit = body["hits"][0]
    assert hit["family_id"] == "fam-auto-0007"
    assert hit["document_version"] == "docver-auto-0007-v1"


def test_search_returns_raw_ungrouped_hits_for_two_versions_of_the_same_family() -> None:
    """Prova que o ai NAO agrupa por familia (isso e responsabilidade
    do backend) - uma consulta com hits em duas versoes da mesma
    familia devolve os dois hits crus, na ordem declarada na fixture.
    """
    client = _client()

    response = client.post(
        "/internal/v1/search",
        json={"query": "auto de infração retificado"},
    )

    assert response.status_code == 200
    hits = response.json()["hits"]
    assert [h["family_id"] for h in hits] == ["fam-auto-0007", "fam-auto-0007"]
    assert [h["document_version"] for h in hits] == [
        "docver-auto-0007-v1",
        "docver-auto-0007-v2",
    ]


def test_search_returns_hits_from_multiple_families_in_declared_order() -> None:
    client = _client()

    response = client.post(
        "/internal/v1/search",
        json={"query": "processo sei 48500.001234/2024-11"},
    )

    assert response.status_code == 200
    hits = response.json()["hits"]
    assert [h["family_id"] for h in hits] == [
        "fam-defesa-0007",
        "fam-decisao-0007",
        "fam-auto-0007",
    ]


def test_search_returns_empty_hits_for_a_query_not_declared_in_the_fixture() -> None:
    client = _client()

    response = client.post(
        "/internal/v1/search",
        json={"query": "consulta que nao existe em nenhuma fixture"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hits"] == []
    assert body["model_version"] == "fixture-demo"


def test_search_respects_top_k_without_reordering() -> None:
    client = _client()

    response = client.post(
        "/internal/v1/search",
        json={"query": "processo sei 48500.001234/2024-11", "top_k": 2},
    )

    hits = response.json()["hits"]
    assert [h["family_id"] for h in hits] == ["fam-defesa-0007", "fam-decisao-0007"]
