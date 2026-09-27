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
