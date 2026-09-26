"""Testes do adapter de embeddings Bedrock Titan V2 (issue #69).

Usa um dublê (``FakeBedrockRuntimeClient``) no lugar do cliente boto3
real - nenhuma chamada de rede/AWS na suite automatizada, conforme a
propria issue pede ("Testes do serviço ai cobrindo ... o adapter de
embeddings (com dublê para a chamada Bedrock)").
"""

import json

import pytest

from app.embeddings import DIMENSIONS, MODEL_ID, BedrockEmbedder


class _FakeBody:
    """Espelha o objeto ``StreamingBody`` que boto3 devolve em
    ``response["body"]`` - so precisa de ``.read()``."""

    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw


class FakeBedrockRuntimeClient:
    """Dublê do cliente boto3 ``bedrock-runtime`` - grava as chamadas
    recebidas e devolve um embedding determinístico (hash do texto),
    sem nenhuma chamada de rede."""

    def __init__(self, dimensions: int = DIMENSIONS) -> None:
        self._dimensions = dimensions
        self.calls: list[dict] = []

    def invoke_model(self, *, modelId: str, body: str, accept: str, contentType: str):
        self.calls.append(
            {
                "modelId": modelId,
                "body": json.loads(body),
                "accept": accept,
                "contentType": contentType,
            }
        )
        text = json.loads(body)["inputText"]
        vector = _deterministic_vector(text, self._dimensions)
        return {
            "body": _FakeBody(
                {"embedding": vector, "inputTextTokenCount": len(text.split())}
            )
        }


class _WrongDimensionsBedrockRuntimeClient:
    def invoke_model(self, *, modelId: str, body: str, accept: str, contentType: str):
        return {"body": _FakeBody({"embedding": [0.1, 0.2, 0.3], "inputTextTokenCount": 1})}


def _deterministic_vector(text: str, dimensions: int) -> list[float]:
    seed = sum(ord(c) for c in text) or 1
    return [((seed * (i + 1)) % 97) / 97 for i in range(dimensions)]


def test_embed_text_calls_bedrock_with_locked_model_config():
    client = FakeBedrockRuntimeClient()
    embedder = BedrockEmbedder(client)

    result = embedder.embed_text("procure precedentes sobre MMGD")

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["modelId"] == MODEL_ID
    assert call["body"] == {
        "inputText": "procure precedentes sobre MMGD",
        "dimensions": DIMENSIONS,
        "normalize": True,
    }
    assert len(result.vector) == DIMENSIONS
    assert result.input_token_count == 4


def test_embed_text_is_deterministic_for_the_same_input():
    embedder = BedrockEmbedder(FakeBedrockRuntimeClient())

    first = embedder.embed_text("mesmo texto")
    second = embedder.embed_text("mesmo texto")

    assert first.vector == second.vector


def test_embed_text_raises_when_bedrock_returns_wrong_dimensions():
    embedder = BedrockEmbedder(_WrongDimensionsBedrockRuntimeClient())

    with pytest.raises(ValueError, match="dimensoes"):
        embedder.embed_text("texto qualquer")
