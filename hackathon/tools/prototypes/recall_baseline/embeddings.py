"""Bedrock Titan Text Embeddings V2 client for the Recall@3 baseline (#60).

Configuration is the one locked in M1
(`requirements/perspec-me/capiwatt-lens-hackathon/concerns/m1-algorithm-model-selection.md`,
"Modelo travado em 2026-09-26") -- not a decision made by this prototype:

- model_id: amazon.titan-embed-text-v2:0
- region: us-east-1
- dimensions: 1024
- normalize: true (unit-length vectors -> dot product == cosine similarity)

Credentials are read from the environment (`source .env` before running).
This module never logs or persists the request/response beyond the
embedding vector and the token count Bedrock reports; it never prints
credentials.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import boto3

MODEL_ID = "amazon.titan-embed-text-v2:0"
REGION = "us-east-1"
DIMENSIONS = 1024
NORMALIZE = True


@dataclass
class EmbeddingResult:
    vector: list[float]
    input_token_count: int


def get_bedrock_runtime_client():
    return boto3.client("bedrock-runtime", region_name=REGION)


def embed_text(client, text: str) -> EmbeddingResult:
    body = json.dumps(
        {
            "inputText": text,
            "dimensions": DIMENSIONS,
            "normalize": NORMALIZE,
        }
    )
    response = client.invoke_model(
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
    return sum(x * y for x, y in zip(a, b))
