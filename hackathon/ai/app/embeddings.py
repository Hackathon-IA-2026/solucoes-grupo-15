"""Adapter de embeddings Bedrock Titan V2 do modulo ai (issue #69).

Porta a configuracao travada em M1
(`requirements/perspec-me/capiwatt-lens-hackathon/concerns/m1-algorithm-model-selection.md`)
e validada pelo protototipo do Recall@3 (issue #60, gate PASSOU -
`hackathon/tools/prototypes/recall_baseline/embeddings.py`): mesmo
modelo, mesma regiao, mesmas dimensoes, mesma normalizacao.

``BedrockEmbedder.embed_text`` recebe o cliente boto3 (ou um dublê nos
testes - ver hackathon/ai/tests/test_embeddings.py) como argumento
explicito, nunca cria a propria conexao AWS por chamada - isso e feito
uma vez por processo (``get_bedrock_runtime_client``) e injetado via
FastAPI ``Depends`` nas rotas (app/routes/index.py, app/routes/search.py).
Nenhuma credencial e lida/logada aqui; boto3 resolve credenciais do
ambiente (variaveis AWS_* ou perfil), nunca hardcoded.

``MODEL_VERSION`` e a constante real usada no envelope de resposta
quando ``EMBEDDER=bedrock`` - identifica modelo, regiao, dimensoes e
normalizacao para reprodutibilidade (i7-reproducibility), tomando o
lugar da constante fixture ``MODEL_VERSION = "fixture-demo"``
(app/routes/index.py) nesse modo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

MODEL_ID = "amazon.titan-embed-text-v2:0"
REGION = "us-east-1"
DIMENSIONS = 1024
NORMALIZE = True

# Identificador real de model_version para o envelope de busca/indexacao
# (issue #69) - toma o lugar de "fixture-demo" quando EMBEDDER=bedrock.
MODEL_VERSION = "amazon.titan-embed-text-v2-us-east-1-1024d-normalized"


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    input_token_count: int


class BedrockRuntimeClient(Protocol):
    """Superficie minima do cliente boto3 ``bedrock-runtime`` usada aqui.

    Documentada como Protocol so para deixar explicito, em testes, o
    que um dublê precisa implementar (``invoke_model``) sem depender do
    SDK real - ver ``FakeBedrockRuntimeClient`` em
    hackathon/ai/tests/test_embeddings.py.
    """

    def invoke_model(self, *, modelId: str, body: str, accept: str, contentType: str): ...


def get_bedrock_runtime_client() -> BedrockRuntimeClient:
    import boto3

    return boto3.client("bedrock-runtime", region_name=REGION)


class BedrockEmbedder:
    """Adapter real do port de embeddings (Titan V2 via Bedrock)."""

    def __init__(self, client: BedrockRuntimeClient) -> None:
        self._client = client

    def embed_text(self, text: str) -> EmbeddingResult:
        body = json.dumps(
            {
                "inputText": text,
                "dimensions": DIMENSIONS,
                "normalize": NORMALIZE,
            }
        )
        response = self._client.invoke_model(
            modelId=MODEL_ID,
            body=body,
            accept="application/json",
            contentType="application/json",
        )
        payload = json.loads(response["body"].read())
        vector = payload["embedding"]
        if len(vector) != DIMENSIONS:
            raise ValueError(
                f"Titan V2 retornou {len(vector)} dimensoes, esperado {DIMENSIONS}"
            )
        return EmbeddingResult(
            vector=vector,
            input_token_count=payload.get("inputTextTokenCount", -1),
        )


def dot_product(a: list[float], b: list[float]) -> float:
    """Similaridade por produto escalar - com vetores normalizados,
    equivalente a similaridade de cosseno (mesma escolha do protototipo)."""
    return sum(x * y for x, y in zip(a, b, strict=True))
