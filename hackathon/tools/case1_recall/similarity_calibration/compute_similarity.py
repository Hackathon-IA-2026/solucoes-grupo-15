"""Matriz de similaridade completa (45 pares) e vizinhos top-3 por
familia, calculada sobre os vetores REAIS de familia (issue #74 --
``family_vectors.py``, que le os vetores brutos reais persistidos pela
issue #73). Mesma metrica de #60/#61: produto interno entre vetores
unitarios (== cosseno).

Roda por cima do resultado, ja em memoria, de ``family_vectors.py`` --
nao faz nenhuma chamada de rede.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from family_vectors import load_family_vectors

OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "family_similarity.json"


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_pairs(families: dict[str, dict]) -> list[dict]:
    pairs = []
    for family_a, family_b in itertools.combinations(sorted(families), 2):
        score = _dot(families[family_a]["vector"], families[family_b]["vector"])
        pairs.append({"family_a": family_a, "family_b": family_b, "score": score})
    pairs.sort(key=lambda p: p["score"], reverse=True)
    return pairs


def compute_top_k_neighbors(families: dict[str, dict], pairs: list[dict], top_k: int = 3) -> dict[str, list[dict]]:
    scores_by_family: dict[str, list[dict]] = {family_id: [] for family_id in families}
    for pair in pairs:
        scores_by_family[pair["family_a"]].append({"family_id": pair["family_b"], "score": pair["score"]})
        scores_by_family[pair["family_b"]].append({"family_id": pair["family_a"], "score": pair["score"]})
    neighbors = {}
    for family_id, scored in scores_by_family.items():
        scored.sort(key=lambda s: s["score"], reverse=True)
        neighbors[family_id] = scored[:top_k]
    return neighbors


def main() -> None:
    families = load_family_vectors()
    pairs = compute_pairs(families)
    neighbors = compute_top_k_neighbors(families, pairs, top_k=3)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "model_version": "amazon.titan-embed-text-v2-us-east-1-1024d-normalized",
                "source": "hackathon/.pipeline-output/documents/_raw_vectors/amazon.titan-embed-text-v2-us-east-1-1024d-normalized.jsonl (issue #73, embeddings reais)",
                "n_families": len(families),
                "n_pairs": len(pairs),
                "families": {
                    family_id: {"n_chunks": info["n_chunks"], "n_motivacao_chunks": info["n_motivacao_chunks"]}
                    for family_id, info in sorted(families.items())
                },
                "pairs": pairs,
                "top_k_neighbors": neighbors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"{len(pairs)} pares calculados -> {OUTPUT_PATH}")
    print("\nTop 10 pares por score:")
    for pair in pairs[:10]:
        print(f"  {pair['score']:.4f}  {pair['family_a']} <-> {pair['family_b']}")


if __name__ == "__main__":
    main()
