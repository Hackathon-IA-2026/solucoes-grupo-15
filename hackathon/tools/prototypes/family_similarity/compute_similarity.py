"""PROTOTYPE — vizinhança vetorial entre famílias e calibração de
`limiar_relacao` / `limiar_fusao` (issue #61).

No new Bedrock calls: reuses the 342 chunk embeddings already computed by
issue #60 (`recall_baseline/output/chunks.jsonl`, Titan V2,
`amazon.titan-embed-text-v2:0`, us-east-1, 1024 dims, normalized), averaged
per document (= per família in this corpus, see `family_vectors.py`).

Similarity metric: dot product between unit-length vectors == cosine
similarity, same metric #60 used, for consistency.

Run:
    python3.12 hackathon/tools/prototypes/family_similarity/compute_similarity.py
"""

from __future__ import annotations

import json
from pathlib import Path

from family_labels import FAMILY_INFO
from family_vectors import load_family_vectors

TOP_K = 3  # fixado, não é decisão desta issue
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def build_matrix(families: dict[str, dict]) -> dict[str, dict[str, float]]:
    ids = sorted(families.keys())
    matrix: dict[str, dict[str, float]] = {i: {} for i in ids}
    for i in ids:
        for j in ids:
            if i == j:
                continue
            matrix[i][j] = dot(families[i]["vector"], families[j]["vector"])
    return matrix


def top_k_neighbors(
    matrix: dict[str, dict[str, float]], k: int = TOP_K
) -> dict[str, list[tuple[str, float]]]:
    neighbors: dict[str, list[tuple[str, float]]] = {}
    for doc_id, scores in matrix.items():
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        neighbors[doc_id] = ranked[:k]
    return neighbors


def short_label(doc_id: str) -> str:
    info = FAMILY_INFO[doc_id]
    return f"{info['document_type']} ({info['official_id']})"


def main() -> None:
    families = load_family_vectors()
    matrix = build_matrix(families)
    neighbors = top_k_neighbors(matrix, TOP_K)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Full pairwise matrix, all C(10,2)=45 unordered pairs, for calibration.
    ids = sorted(families.keys())
    pairs = []
    for i_idx, i in enumerate(ids):
        for j in ids[i_idx + 1 :]:
            pairs.append(
                {
                    "family_a": i,
                    "family_b": j,
                    "process_a": families[i]["process_nup_canonical"],
                    "process_b": families[j]["process_nup_canonical"],
                    "same_process_group": (
                        families[i]["process_nup_canonical"]
                        == families[j]["process_nup_canonical"]
                    ),
                    "score": matrix[i][j],
                }
            )
    pairs.sort(key=lambda p: p["score"], reverse=True)

    result = {
        "model_id": "amazon.titan-embed-text-v2:0",
        "region": "us-east-1",
        "dimensions": 1024,
        "similarity_metric": "dot_product_on_unit_vectors (== cosine)",
        "family_vector_strategy": "mean_of_chunk_embeddings_then_l2_renormalized",
        "top_k": TOP_K,
        "n_families": len(families),
        "families": {
            doc_id: {
                "n_chunks": info["n_chunks"],
                "process_nup_canonical": info["process_nup_canonical"],
                "document_type": FAMILY_INFO[doc_id]["document_type"],
                "official_id": FAMILY_INFO[doc_id]["official_id"],
                "agent": FAMILY_INFO[doc_id]["agent"],
            }
            for doc_id, info in families.items()
        },
        "top_k_neighbors": {
            doc_id: [{"neighbor": n, "score": s} for n, s in ranked]
            for doc_id, ranked in neighbors.items()
        },
        "all_pairs_sorted_desc": pairs,
    }

    out_path = OUTPUT_DIR / "family_similarity.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"{len(families)} famílias, {len(pairs)} pares únicos calculados.")
    print(f"Escrito em {out_path}")
    print()
    print("Top 10 pares por score:")
    for p in pairs[:10]:
        print(
            f"  {p['score']:.4f}  {short_label(p['family_a'])!r} <-> "
            f"{short_label(p['family_b'])!r}  "
            f"(mesmo grupo de processo: {p['same_process_group']})"
        )
    print()
    print("Bottom 5 pares por score:")
    for p in pairs[-5:]:
        print(
            f"  {p['score']:.4f}  {short_label(p['family_a'])!r} <-> "
            f"{short_label(p['family_b'])!r}  "
            f"(mesmo grupo de processo: {p['same_process_group']})"
        )
    print()
    print("Top-3 vizinhos por família:")
    for doc_id in ids:
        print(f"  {doc_id}:")
        for n, s in neighbors[doc_id]:
            print(f"    {s:.4f}  {n}")


if __name__ == "__main__":
    main()
