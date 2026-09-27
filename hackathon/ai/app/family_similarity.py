"""Vizinhanca vetorial entre familias - operacao ``similar_families`` do
port VectorService (issue #92; contrato em
requirements/contracts/backend-vector-service.md).

Vetor de familia = media dos embeddings de todos os chunks da familia no
indice, renormalizada para norma unitaria; score = produto interno entre
vetores de familia (== cosseno). E exatamente a agregacao sobre a qual
``limiar_relacao``/``limiar_fusao`` foram calibrados nas issues #61/#74
(ver hackathon/tools/case1_recall/similarity_calibration/family_vectors.py,
decisao "mean-of-all-chunks mantido" em d14-data-operations-modeling) -
mudar a agregacao aqui invalida aquela calibracao.

O ai so entrega candidatos: nenhum limiar e aplicado aqui. Classificar
em ``similar_a``/sugestao de fusao/descartado e gravar arestas e do
backend (app/ai_relations.py do backend).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class UnknownFamily(LookupError):
    """``family_id`` sem nenhum chunk no indice."""


@dataclass(frozen=True)
class SimilarFamily:
    family_id: str
    score: float


def family_vector(embeddings: list[list[float]]) -> list[float]:
    dims = len(embeddings[0])
    total = [0.0] * dims
    for embedding in embeddings:
        for i, value in enumerate(embedding):
            total[i] += value
    norm = math.sqrt(sum(x * x for x in total))
    if norm == 0.0:
        return total
    return [x / norm for x in total]


def similar_families(
    family_id: str, embeddings_by_family: dict[str, list[list[float]]], top_k: int
) -> list[SimilarFamily]:
    """Os ``top_k`` vizinhos de ``family_id`` por score decrescente (empate
    desfeito por ``family_id``), nunca a propria familia."""
    if not embeddings_by_family.get(family_id):
        raise UnknownFamily(family_id)
    vectors = {fid: family_vector(embs) for fid, embs in embeddings_by_family.items() if embs}
    target = vectors[family_id]
    scored = [
        SimilarFamily(fid, sum(x * y for x, y in zip(target, vector, strict=True)))
        for fid, vector in vectors.items()
        if fid != family_id
    ]
    scored.sort(key=lambda s: (-s.score, s.family_id))
    return scored[:top_k]
