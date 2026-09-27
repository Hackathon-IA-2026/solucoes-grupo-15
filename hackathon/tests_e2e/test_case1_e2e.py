"""Suite e2e backend <-> banco vetorial sobre os artefatos reais do caso 1 (issue #88).

Cada teste exercita as rotas publicas ``/v1/*`` do backend via HTTP, com o
ai real atras (sem dependency override do ``AiClient``), OpenSearch real e
Postgres real - ver conftest.py. Os testes que mudam o estado
compartilhado (``stale_corpus``, reindex e delete) restauram o estado que
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
from urllib.parse import quote

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
# delete(document_version) (#98)
# ---------------------------------------------------------------------------


def _ai_search_versions(stack: Stack) -> set[str]:
    """document_versions devolvidas pelo ``ai`` numa busca larga (``top_k``
    acima dos 342 chunks do caso 1). O k-NN (HNSW) e aproximado e nao
    devolve todo chunk, entao isto so serve para presenca/ausencia de
    versao; contagem exata vem de ``_chunk_counts``."""
    response = httpx.post(
        f"{stack.ai_url}/internal/v1/search",
        json={"query": CAROLINA_QUERY, "top_k": 500},
        timeout=60.0,
    )
    assert response.status_code == 200, response.text
    return {hit["document_version"] for hit in response.json()["hits"]}


def test_delete_document_version_removes_only_its_chunks_from_search(
    stack: Stack, backend: httpx.Client, ingested: dict, corpus_version: str
) -> None:
    """Indexado o caso 1, apagar uma versao pelo ``ai`` tira da busca todos
    os chunks dela e so dela. Restaura o estado reingerindo pelo backend: o
    ``ai`` esqueceu a versao, entao a reingestao a reindexa de verdade."""
    before = _search(backend, top_k=10, limit=10)
    counts_before = _chunk_counts(stack)
    target = before["results"][0]["document_version"]
    assert _ai_search_versions(stack) == set(counts_before)

    try:
        response = httpx.delete(f"{stack.ai_url}/internal/v1/documents/{target}")
        again = httpx.delete(f"{stack.ai_url}/internal/v1/documents/{target}")

        assert response.status_code == 200, response.text
        assert response.json() == {
            "document_version": target,
            "model_version": MODEL_VERSION,
            "chunks_deleted": counts_before[target],
        }
        assert again.status_code == 200
        assert again.json()["chunks_deleted"] == 0

        others = {dv: n for dv, n in counts_before.items() if dv != target}
        assert _ai_search_versions(stack) == set(others)
        assert _chunk_counts(stack) == others
        after = _search(backend, top_k=10, limit=10)
        assert after["results"]
        assert all(r["document_version"] != target for r in after["results"])
    finally:
        ingest_case1(backend, corpus_version)

    assert _chunk_counts(stack) == counts_before
    assert _ranking(_search(backend, top_k=10, limit=10)) == _ranking(before)


# ---------------------------------------------------------------------------
# Relacoes vindas do ai (issue #92)
# ---------------------------------------------------------------------------

# Calibracao da #74 sobre os mesmos vetores brutos da #73 (versionada): os
# vizinhos top-3 por familia e a classificacao de cada par com
# limiar_relacao=0.80 / limiar_fusao=0.97.
CALIBRATION_REPORT = (
    HACKATHON_DIR
    / "tools"
    / "case1_recall"
    / "similarity_calibration"
    / "output"
    / "calibration_report.json"
)
CASE1_FAMILIES = sorted(dv.rsplit("-", 1)[0] for dv in CASE1_DOCUMENT_VERSIONS)
# Citacoes "Auto de Infração nº ..." do texto real que apontam para um auto
# do proprio corpus (levantadas lendo os Markdown da #59), fonte -> alvo.
EXPECTED_REFERENCE_EDGES = {
    ("case1-cemig-recurso", "case1-cemig-auto"),
    ("case1-cemig-voto", "case1-cemig-auto"),
    ("case1-enel-recurso", "case1-enel-auto"),
    ("case1-enel-voto", "case1-enel-auto"),
    ("case1-coelba-recurso", "case1-coelba-auto"),
    ("case1-coelba-complemento", "case1-coelba-auto"),
    ("case1-coelba-voto", "case1-coelba-auto"),
}


def _calibration() -> dict:
    return json.loads(CALIBRATION_REPORT.read_text(encoding="utf-8"))


def _all_graph_edges(backend: httpx.Client) -> list[tuple[str, dict]]:
    edges = []
    for family_id in CASE1_FAMILIES:
        response = backend.get(f"/v1/documents/{family_id}/graph")
        assert response.status_code == 200, response.text
        edges.extend((family_id, edge) for edge in response.json()["edges"])
    return edges


def test_similar_families_reproduces_issue_74_neighbors(stack: Stack, ingested: dict) -> None:
    expected = _calibration()["top_k_neighbors"]

    for family_id in CASE1_FAMILIES:
        response = httpx.get(
            f"{stack.ai_url}/internal/v1/families/{family_id}/similar", params={"top_k": 3}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["model_version"] == MODEL_VERSION
        got = [(n["family_id"], n["score"]) for n in body["similar"]]
        want = [(n["family_id"], n["score"]) for n in expected[family_id]]
        assert [fid for fid, _ in got] == [fid for fid, _ in want], family_id
        for (_, got_score), (_, want_score) in zip(got, want, strict=True):
            assert got_score == pytest.approx(want_score, abs=1e-6)


def test_relations_from_ai_appear_in_graph(
    stack: Stack, backend: httpx.Client, ingested: dict
) -> None:
    calibration = _calibration()
    expected_similar = {
        frozenset((p["family_a"], p["family_b"])): p["score"]
        for p in calibration["pairs"]
        if p["classification"] == "similar_a"
    }
    assert len(expected_similar) == calibration["counts_by_classification"]["similar_a"] == 11

    edges = _all_graph_edges(backend)

    similar = {
        frozenset((node, e["neighbor_id"])): e for node, e in edges if e["type"] == "similar_a"
    }
    assert set(similar) == set(expected_similar)
    for pair, edge in similar.items():
        assert (edge["origin"], edge["status"]) == ("similarity", "suggested")
        assert edge["score"] == pytest.approx(expected_similar[pair], abs=1e-6)
        assert 0.80 <= edge["score"] < 0.97
    positive = frozenset(calibration["known_positive_pair"]["families"])
    assert positive in similar

    references = {
        (node, e["neighbor_id"]): e
        for node, e in edges
        if e["type"] == "referencia" and e["evidence"]["document_version"].startswith(node)
    }
    assert set(references) == EXPECTED_REFERENCE_EDGES
    for edge in references.values():
        assert (edge["origin"], edge["status"]) == ("explicit", "confirmed")
        # o locator e o chunk_id ("<versao>#chunk-NNNN"): "#" precisa de escape na URL
        chunk_id = quote(edge["evidence"]["locator"], safe="")
        chunk = httpx.get(f"{stack.opensearch_url}/{INDEX_NAME}/_doc/{chunk_id}")
        assert chunk.status_code == 200, chunk.text
        assert "Infração" in chunk.json()["_source"]["text"]


def test_ai_relations_survive_reingestion_without_duplicates(
    backend: httpx.Client, ingested: dict, corpus_version: str
) -> None:
    before = sorted(
        (node, e["type"], e["neighbor_id"]) for node, e in _all_graph_edges(backend)
    )

    ingest_case1(backend, corpus_version)

    after = sorted((node, e["type"], e["neighbor_id"]) for node, e in _all_graph_edges(backend))
    assert after == before
    assert ingested["relations_count"] == 11 + len(EXPECTED_REFERENCE_EDGES)


# ---------------------------------------------------------------------------
# Divergencias conhecidas (xfail estrito - ver docstring do modulo)
# ---------------------------------------------------------------------------


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


# Chaves que hackathon/frontend/src/api/search.ts declara e le desde a #93:
# o envelope plano por chunk (SearchEnvelope) e cada resultado (SearchResult).
FRONTEND_SEARCH_ENVELOPE_KEYS = {
    "request_id",
    "data_mode",
    "corpus_version",
    "model_version",
    "ranking_version",
    "results",
    "total",
    "next_cursor",
    "stale_corpus",
}
FRONTEND_SEARCH_RESULT_KEYS = {
    "family_id",
    "document_version",
    "chunk_id",
    "chunk_index",
    "excerpt",
    "score",
    "localizador",
    "document_type",
    "document_id",
    "processo_numero",
    "version_date",
}


def test_frontend_search_shape_matches_real_envelope(
    backend: httpx.Client, ingested: dict
) -> None:
    """Issue #93: o envelope real tem exatamente as chaves que o frontend
    le, e a continuacao que o "carregar mais" envia (``{query, cursor}``)
    devolve a cauda do mesmo conjunto congelado, na mesma ordem."""
    first = _search(backend, top_k=10, limit=4)

    assert set(first) >= FRONTEND_SEARCH_ENVELOPE_KEYS, sorted(first)
    assert first["results"]
    for result in first["results"]:
        assert set(result) == FRONTEND_SEARCH_RESULT_KEYS, sorted(result)
    assert first["total"] == 10
    assert first["next_cursor"] is not None
    assert first["stale_corpus"] is False

    # Corpo exato de frontend/src/api/search.ts::searchDocuments(query, cursor).
    continuation = backend.post(
        "/v1/search", json={"query": CAROLINA_QUERY, "cursor": first["next_cursor"]}
    )
    assert continuation.status_code == 200, continuation.text
    rest = continuation.json()

    assert rest["request_id"] == first["request_id"]
    assert rest["next_cursor"] is None
    whole = _search(backend, top_k=10, limit=10)["results"]
    assert _ranking({"results": first["results"] + rest["results"]}) == _ranking(
        {"results": whole}
    )


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
