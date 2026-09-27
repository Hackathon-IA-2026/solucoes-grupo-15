"""Contrato HTTP do AiClient (issue #69).

Prova que ``index``/``reindex`` enviam ``family_id``/``corpus_version``
por documento no corpo da requisicao a /internal/v1/index e
/internal/v1/reindex - o que o ai real (EMBEDDER=bedrock) precisa para
gravar/filtrar por esses atributos no indice vetorial (ver
requirements/contracts/backend-vector-service.md). Usa
``httpx.MockTransport`` (sem servidor real, sem rede) - o mesmo padrao
que o resto do backend usa para isolar chamadas HTTP externas.
"""

import json

import httpx

from app.clients.ai_client import AiClient, IndexDocumentPayload


def test_index_sends_family_id_and_corpus_version_per_document(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "reports": [
                    {
                        "document_version": "docver-1",
                        "extracted_text_locator": "/data/documents/docver-1/extracted.txt",
                        "chunks_indexed": 1,
                        "model_version": "amazon.titan-embed-text-v2-us-east-1-1024d-normalized",
                    }
                ]
            },
        )

    def fake_post(url, *, json=None, timeout=None):
        request = httpx.Request("POST", url, json=json)
        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as http_client:
            return http_client.send(request)

    monkeypatch.setattr("app.clients.ai_client.httpx.post", fake_post)

    client = AiClient(base_url="http://ai-test")
    reports = client.index(
        [
            IndexDocumentPayload(
                document_version="docver-1",
                text="texto do documento",
                family_id="fam-1",
                corpus_version="corpus-v1",
            )
        ]
    )

    assert captured["body"] == {
        "documents": [
            {
                "document_version": "docver-1",
                "text": "texto do documento",
                "family_id": "fam-1",
                "corpus_version": "corpus-v1",
            }
        ]
    }
    assert reports[0].model_version == "amazon.titan-embed-text-v2-us-east-1-1024d-normalized"


def test_index_omits_family_id_and_corpus_version_when_absent(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "reports": [
                    {
                        "document_version": "docver-1",
                        "extracted_text_locator": "/data/documents/docver-1/extracted.txt",
                        "chunks_indexed": 1,
                        "model_version": "fixture-demo",
                    }
                ]
            },
        )

    def fake_post(url, *, json=None, timeout=None):
        request = httpx.Request("POST", url, json=json)
        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as http_client:
            return http_client.send(request)

    monkeypatch.setattr("app.clients.ai_client.httpx.post", fake_post)

    client = AiClient(base_url="http://ai-test")
    client.index([IndexDocumentPayload(document_version="docver-1", text="texto")])

    assert captured["body"] == {
        "documents": [{"document_version": "docver-1", "text": "texto"}]
    }


def test_reindex_posts_to_reindex_endpoint_with_same_document_shape(monkeypatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"reports": []})

    def fake_post(url, *, json=None, timeout=None):
        captured["called_url"] = url
        request = httpx.Request("POST", url, json=json)
        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as http_client:
            return http_client.send(request)

    monkeypatch.setattr("app.clients.ai_client.httpx.post", fake_post)

    client = AiClient(base_url="http://ai-test")
    client.reindex(
        [
            IndexDocumentPayload(
                document_version="docver-1",
                text="texto",
                family_id="fam-1",
                corpus_version="corpus-v1",
            )
        ]
    )

    assert captured["called_url"] == "http://ai-test/internal/v1/reindex"
    assert captured["body"]["documents"][0]["family_id"] == "fam-1"


def test_similar_families_gets_candidates_for_the_family(monkeypatch) -> None:
    # issue #92: similar_families(family_id, top_k) -> [{family_id, score}]
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "family_id": "fam-a",
                "model_version": "amazon.titan-embed-text-v2-us-east-1-1024d-normalized",
                "similar": [{"family_id": "fam-b", "score": 0.91}],
            },
        )

    def fake_get(url, *, params=None, timeout=None):
        request = httpx.Request("GET", url, params=params)
        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            return http_client.send(request)

    monkeypatch.setattr("app.clients.ai_client.httpx.get", fake_get)

    similar = AiClient(base_url="http://ai-test").similar_families("fam-a", top_k=3)

    assert captured["url"] == "http://ai-test/internal/v1/families/fam-a/similar?top_k=3"
    assert [(s.family_id, s.score) for s in similar] == [("fam-b", 0.91)]


def test_index_report_parses_references(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "reports": [
                    {
                        "document_version": "docver-1",
                        "extracted_text_locator": "/data/documents/docver-1/extracted.txt",
                        "chunks_indexed": 1,
                        "model_version": "m",
                        "references": [
                            {
                                "identifier_raw": "Auto de Infração nº 0017/2020-SFE",
                                "relation_type": None,
                                "locator": "docver-1#chunk-0000",
                            }
                        ],
                    }
                ]
            },
        )

    def fake_post(url, *, json=None, timeout=None):
        request = httpx.Request("POST", url, json=json)
        with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
            return http_client.send(request)

    monkeypatch.setattr("app.clients.ai_client.httpx.post", fake_post)

    [report] = AiClient(base_url="http://ai-test").index(
        [IndexDocumentPayload(document_version="docver-1", text="t")]
    )

    [reference] = report.references
    assert reference.identifier_raw == "Auto de Infração nº 0017/2020-SFE"
    assert reference.relation_type is None
    assert reference.locator == "docver-1#chunk-0000"


def test_ingestion_client_waits_for_real_indexing_but_search_stays_short(monkeypatch) -> None:
    """Issue #106: no primeiro ``POST /v1/ingestions`` na AWS (ECS Exec),
    o ai levou mais de 10 s para indexar o corpus demo com Bedrock e o
    backend devolveu 500 (``httpx.ReadTimeout``), embora o ai tenha
    terminado a indexacao. ``index``/``reindex`` fazem uma chamada
    Bedrock por chunk dentro de uma unica requisicao - o mesmo motivo do
    timeout de 900 s em ``tools/case1_recall/seed_and_measure.py``. A
    busca e o health continuam curtos para nao prender a requisicao do
    usuario com o ai fora do ar."""
    timeouts: dict[str, float] = {}

    def fake_post(url, *, json=None, timeout=None):
        timeouts[url.rsplit("/", 1)[-1]] = timeout
        if url.endswith("/search"):
            return httpx.Response(
                200,
                json={"hits": [], "model_version": "m"},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(200, json={"reports": []}, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.clients.ai_client.httpx.post", fake_post)

    from app.clients.ai_client import get_ai_client

    client = get_ai_client()
    doc = IndexDocumentPayload(document_version="d", text="t", family_id="f", corpus_version="c")
    client.index([doc])
    client.reindex([doc])
    client.search("pergunta")

    assert timeouts["index"] >= 900
    assert timeouts["reindex"] >= 900
    assert timeouts["search"] == 10.0
