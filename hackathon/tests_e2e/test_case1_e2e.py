"""Suite e2e backend <-> banco vetorial sobre os artefatos reais do caso 1 (issue #88).

Cada teste exercita as rotas publicas ``/v1/*`` do backend via HTTP, com o
ai real atras (sem dependency override do ``AiClient``), OpenSearch real e
Postgres real - ver conftest.py. Os testes que mudam o estado
compartilhado (``stale_corpus`` e reindex) restauram o estado que
encontraram, para que a ordem de execucao nao importe.

Testes ``xfail(strict=True)`` documentam divergencias conhecidas entre o
contrato (requirements/contracts/backend-vector-service.md) e o
comportamento real; quando a funcionalidade chegar, o xfail estrito vira
falha e obriga a remover a marcacao.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import httpx
import pytest
from process_aggregation import GOLDEN_TOP3_PROCESSES, canonical_process_for

from conftest import HACKATHON_DIR, MODEL_VERSION, Stack, ingest_case1

CAROLINA_QUERY = (
    "procure precedentes sobre fiscalização de atendimento a solicitações de conexão de MMGD"
)
# ai/app/vector_store.py::index_name_for_model_version - MODEL_VERSION ja e um slug valido.
INDEX_NAME = f"capiwatt-chunks-{MODEL_VERSION}"
REINDEX_FROM_RAW_SCRIPT = HACKATHON_DIR / "tools" / "case1_recall" / "reindex_from_raw_vectors.py"
CASE1_DOCUMENT_VERSIONS = {
    "case1-cemig-auto-2020",
    "case1-cemig-recurso-2020",
    "case1-cemig-voto-2023",
    "case1-coelba-auto-2025",
    "case1-coelba-complemento-2025",
    "case1-coelba-recurso-2025",
    "case1-coelba-voto-2025",
    "case1-enel-auto-2018",
    "case1-enel-recurso-2019",
    "case1-enel-voto-2020",
}


def _search(backend: httpx.Client, **body) -> dict:
    response = backend.post("/v1/search", json={"query": CAROLINA_QUERY, **body})
    assert response.status_code == 200, response.text
    return response.json()


def _chunk_counts(stack: Stack) -> dict[str, int]:
    """Chunks por document_version no indice OpenSearch real."""
    response = httpx.post(
        f"{stack.opensearch_url}/{INDEX_NAME}/_search",
        json={
            "size": 0,
            "aggs": {"por_versao": {"terms": {"field": "document_version", "size": 100}}},
        },
    )
    response.raise_for_status()
    buckets = response.json()["aggregations"]["por_versao"]["buckets"]
    return {b["key"]: b["doc_count"] for b in buckets}


def _raw_vector_chunk_ids(stack: Stack) -> set[str]:
    """Replay do JSONL da #73 (mesma regra de ai/app/raw_vectors.py)."""
    chunks: dict[str, str] = {}
    for line in stack.raw_vectors_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if "_tombstone" in record:
            chunks = {cid: dv for cid, dv in chunks.items() if dv != record["_tombstone"]}
        else:
            chunks[record["chunk_id"]] = record["document_version"]
    return set(chunks)


def _ranking(envelope: dict) -> list[tuple[str, str, float]]:
    return [(r["document_version"], r["excerpt"], r["score"]) for r in envelope["results"]]


# ---------------------------------------------------------------------------
# Ingestao
# ---------------------------------------------------------------------------


def test_ingestion_indexes_case1_in_real_opensearch(
    stack: Stack, backend: httpx.Client, ingested: dict
) -> None:
    assert ingested["versions_count"] == 10

    counts = _chunk_counts(stack)

    assert set(counts) == CASE1_DOCUMENT_VERSIONS
    # O chunking do ai reproduz exatamente os chunks embedados na #73.
    assert sum(counts.values()) == len(_raw_vector_chunk_ids(stack))


def test_catalog_records_locator_and_manifest_corpus_version(
    backend: httpx.Client, ingested: dict, corpus_version: str
) -> None:
    envelope = _search(backend, top_k=10, limit=10)

    assert envelope["corpus_version"] == corpus_version
    for result in envelope["results"]:
        locator = f"/data/documents/{result['document_version']}/extracted.txt"
        assert result["localizador"] == locator

    # O texto extraido servido pelo catalogo e o Markdown completo da #59.
    family = backend.get("/v1/documents/case1-cemig-auto")
    assert family.status_code == 200
    expected = (
        HACKATHON_DIR
        / "data"
        / "case-1-carolina-mmgd"
        / "48500.000639-2019-07"
        / "auto-infracao-48500.000639-2019-07.md"
    ).read_text("utf-8")
    assert family.json()["selected_version"]["text"] == expected


def test_reingestion_is_idempotent(
    stack: Stack, backend: httpx.Client, ingested: dict, corpus_version: str
) -> None:
    before = _chunk_counts(stack)

    ingest_case1(backend, corpus_version)

    assert _chunk_counts(stack) == before


# ---------------------------------------------------------------------------
# Busca real
# ---------------------------------------------------------------------------


def test_real_search_envelope_and_recall_at_3(
    backend: httpx.Client, ingested: dict, corpus_version: str
) -> None:
    envelope = _search(backend, top_k=3)

    expected_data_mode = "real"  # cached e bedrock servem vetores Titan V2 reais
    assert envelope["data_mode"] == expected_data_mode
    assert envelope["model_version"] == MODEL_VERSION
    assert envelope["corpus_version"] == corpus_version
    assert len(envelope["results"]) == 3
    assert all(r["document_version"] in CASE1_DOCUMENT_VERSIONS for r in envelope["results"])

    retrieved = {canonical_process_for(r["processo_numero"]) for r in envelope["results"]}
    recall_at_3 = len(retrieved & GOLDEN_TOP3_PROCESSES) / len(GOLDEN_TOP3_PROCESSES)
    assert recall_at_3 >= 2 / 3, (retrieved, recall_at_3)


def test_search_hits_carry_stable_chunk_ids_from_the_index(
    stack: Stack, backend: httpx.Client, ingested: dict
) -> None:
    """Issue #96: cada resultado aponta para um chunk real do indice
    (``chunk_id`` dos vetores brutos da #73) e ``chunk_index`` e o indice
    do chunk no documento - o mesmo chunk tem o mesmo ``chunk_index`` em
    consultas cujas listas tem tamanhos (e posicoes) diferentes."""
    raw_chunk_ids = _raw_vector_chunk_ids(stack)
    wide = _search(backend, top_k=10, limit=10)["results"]
    narrow = _search(backend, top_k=3, limit=3)["results"]

    for result in wide + narrow:
        assert result["chunk_id"] in raw_chunk_ids
        assert result["chunk_id"] == (
            f"{result['document_version']}#chunk-{result['chunk_index']:04d}"
        )
    index_by_chunk = {r["chunk_id"]: r["chunk_index"] for r in wide}
    shared = [r for r in narrow if r["chunk_id"] in index_by_chunk]
    assert shared
    assert all(index_by_chunk[r["chunk_id"]] == r["chunk_index"] for r in shared)
    # Chunk estavel != posicao na lista: algum hit real nao e o chunk 0..n-1 da lista.
    assert [r["chunk_index"] for r in wide] != list(range(len(wide)))


# ---------------------------------------------------------------------------
# Paginacao (#76/#78)
# ---------------------------------------------------------------------------


def test_pagination_continuation_does_not_call_ai(
    stack: Stack, backend: httpx.Client, ingested: dict
) -> None:
    if not stack.managed:
        pytest.skip("contagem de chamadas ao ai le o log do Compose gerenciado pela suite")

    calls_before = stack.ai_search_calls()
    first = _search(backend, top_k=10, limit=4)
    assert stack.ai_search_calls() == calls_before + 1

    pages = [first]
    while pages[-1]["next_cursor"] is not None:
        pages.append(_search(backend, cursor=pages[-1]["next_cursor"], limit=4))
    assert stack.ai_search_calls() == calls_before + 1

    assert [len(p["results"]) for p in pages] == [4, 4, 2]
    assert all(p["total"] == 10 for p in pages)
    assert {p["request_id"] for p in pages} == {first["request_id"]}

    concatenated = [r for p in pages for r in p["results"]]
    keys = [(-r["score"], r["document_version"], r["chunk_index"]) for r in concatenated]
    assert keys == sorted(keys)
    # Mesma lista congelada que uma pagina unica devolveria.
    single_page = _search(backend, top_k=10, limit=10)
    assert _ranking({"results": concatenated}) == _ranking(single_page)


# ---------------------------------------------------------------------------
# Replay (#77)
# ---------------------------------------------------------------------------


def test_replay_matches_fresh_search(backend: httpx.Client, ingested: dict) -> None:
    envelope = _search(backend, top_k=5, limit=5)

    response = backend.post(f"/v1/search/{envelope['request_id']}/replay")

    assert response.status_code == 200
    assert response.json()["matches"] is True


# ---------------------------------------------------------------------------
# Feedback (#82)
# ---------------------------------------------------------------------------


def test_feedback_on_real_chunk_hit(backend: httpx.Client, ingested: dict) -> None:
    envelope = _search(backend, top_k=3)
    hit = envelope["results"][0]

    response = backend.post(
        "/v1/feedback",
        json={
            "request_id": envelope["request_id"],
            "document_version": hit["document_version"],
            "chunk_index": hit["chunk_index"],
            "vote": "up",
        },
    )
    assert response.status_code == 200, response.text

    listed = backend.get("/v1/feedback", params={"request_id": envelope["request_id"]}).json()
    assert [(f["document_version"], f["chunk_index"], f["vote"]) for f in listed] == [
        (hit["document_version"], hit["chunk_index"], "up")
    ]


# ---------------------------------------------------------------------------
# Stale corpus (#79)
# ---------------------------------------------------------------------------


def test_stale_corpus_after_newer_ingestion(
    backend: httpx.Client, ingested: dict, corpus_version: str
) -> None:
    old_search = _search(backend, top_k=10, limit=4)
    assert old_search["stale_corpus"] is False

    try:
        ingest_case1(backend, f"{corpus_version}-e2e-mais-novo")
        continuation = _search(backend, cursor=old_search["next_cursor"], limit=4)
    finally:
        ingest_case1(backend, corpus_version)

    assert continuation["stale_corpus"] is True
    assert continuation["corpus_version"] == corpus_version


# ---------------------------------------------------------------------------
# Reindex a partir dos vetores brutos (#73)
# ---------------------------------------------------------------------------


def test_reindex_from_raw_vectors_preserves_ranking(
    stack: Stack, backend: httpx.Client, ingested: dict
) -> None:
    before = _search(backend, top_k=10, limit=10)
    counts_before = _chunk_counts(stack)

    env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}
    env["OPENSEARCH_URL"] = stack.opensearch_url
    env["RAW_VECTORS_PATH"] = str(stack.raw_vectors_path)
    result = subprocess.run(
        [sys.executable, str(REINDEX_FROM_RAW_SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    assert _chunk_counts(stack) == counts_before
    after = _search(backend, top_k=10, limit=10)
    assert _ranking(after) == _ranking(before)


# ---------------------------------------------------------------------------
# Divergencias conhecidas (xfail estrito - ver docstring do modulo)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "ai nao implementa similar_families (/internal/v1/families/{id}/similar) nem "
        "references[] no IndexReport; backend nao grava arestas vindas do ai"
    ),
)
def test_relations_from_ai_appear_in_graph(
    stack: Stack, backend: httpx.Client, ingested: dict
) -> None:
    similar = httpx.get(
        f"{stack.ai_url}/internal/v1/families/case1-cemig-auto/similar", params={"top_k": 3}
    )
    assert similar.status_code == 200, similar.text

    graph = backend.get("/v1/documents/case1-cemig-auto/graph")
    assert graph.status_code == 200, graph.text
    assert any(edge["origin"] != "explicit" for edge in graph.json()["edges"])


@pytest.mark.xfail(
    strict=True,
    reason="#66 aberta: GET /v1/processos/{processo_numero}/resultado nao existe",
)
def test_processo_resultado_envelope(backend: httpx.Client, ingested: dict) -> None:
    response = backend.get("/v1/processos/48500.000639/2019-07/resultado")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence_refs"]
    for ref in body["evidence_refs"]:
        assert ref["document_version"] in CASE1_DOCUMENT_VERSIONS

    assert backend.get("/v1/processos/00000.000000/0000-00/resultado").status_code == 404


# Chaves que hackathon/frontend/src/api/search.ts (SearchEnvelope/SearchResult)
# declara e le de cada resultado.
FRONTEND_SEARCH_RESULT_KEYS = {"family_id", "face", "matched_chunks"}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "frontend/src/api/search.ts ainda espera resultados agrupados por familia "
        "(face/matched_chunks), removidos na #78"
    ),
)
def test_frontend_search_shape_matches_real_envelope(
    backend: httpx.Client, ingested: dict
) -> None:
    envelope = _search(backend, top_k=3)

    for result in envelope["results"]:
        assert FRONTEND_SEARCH_RESULT_KEYS <= set(result), sorted(result)


# Chaves que hackathon/frontend/src/api/feedback.ts (submitFeedback) envia no
# corpo de POST /v1/feedback desde a #94: a chave por chunk, sem family_id.
FRONTEND_FEEDBACK_PAYLOAD_KEYS = {"request_id", "document_version", "chunk_index", "vote"}


def test_frontend_feedback_payload_is_accepted(backend: httpx.Client, ingested: dict) -> None:
    envelope = _search(backend, top_k=3)
    hit = envelope["results"][0]
    payload = {
        "request_id": envelope["request_id"],
        "document_version": hit["document_version"],
        "chunk_index": hit["chunk_index"],
        "vote": "up",
    }
    assert set(payload) == FRONTEND_FEEDBACK_PAYLOAD_KEYS

    response = backend.post("/v1/feedback", json=payload)

    assert response.status_code == 200, response.text
    stored = response.json()
    assert (stored["document_version"], stored["chunk_index"], stored["family_id"]) == (
        hit["document_version"],
        hit["chunk_index"],
        None,
    )
