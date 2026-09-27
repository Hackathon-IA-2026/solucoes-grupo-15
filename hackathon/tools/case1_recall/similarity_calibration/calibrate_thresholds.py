"""Recalibracao de ``limiar_relacao``/``limiar_fusao`` (issue #74) contra
os vetores REAIS de familia do caso 1 (embeddings persistidos pela issue
#73, via ``family_vectors.py``) -- substitui a calibracao da issue #61,
que usava os embeddings do protototipo do Recall@3 (#60).

Classifica os 45 pares em ``sem_relacao`` / ``similar_a`` /
``sugestao_fusao`` pelos limiares vigentes e reporta a distribuicao de
similaridade em tres grupos (AC da issue #74):

- ``mesmo_processo``: par de familias do mesmo ``process_group`` (D16).
- ``mesmo_tema``: mesmo ``document_type``, ``process_group`` diferente.
- ``temas_diferentes``: ``document_type`` diferente e ``process_group``
  diferente (o resto).

Ver README.md, "Recalibracao (issue #74)", para a leitura desses numeros.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from compute_similarity import compute_pairs, compute_top_k_neighbors
from family_labels import FAMILY_INFO
from family_vectors import load_family_vectors

LIMIAR_RELACAO = 0.80
LIMIAR_FUSAO = 0.97
TOP_K = 3

OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "calibration_report.json"

KNOWN_POSITIVE_PAIR = frozenset({"case1-coelba-recurso", "case1-coelba-complemento"})
KNOWN_CONTROL_PAIR = frozenset({"case1-cemig-auto", "case1-enel-auto"})


def classify(score: float) -> str:
    if score >= LIMIAR_FUSAO:
        return "sugestao_fusao"
    if score >= LIMIAR_RELACAO:
        return "similar_a"
    return "sem_relacao"


def bucket_for(family_a: str, family_b: str) -> str:
    info_a = FAMILY_INFO[family_a]
    info_b = FAMILY_INFO[family_b]
    if info_a["process_group"] == info_b["process_group"]:
        return "mesmo_processo"
    if info_a["document_type"] == info_b["document_type"]:
        return "mesmo_tema"
    return "temas_diferentes"


def _describe(scores: list[float]) -> dict:
    if not scores:
        return {"n": 0}
    return {
        "n": len(scores),
        "min": min(scores),
        "max": max(scores),
        "mean": statistics.mean(scores),
        "median": statistics.median(scores),
    }


def main() -> None:
    families = load_family_vectors()
    pairs = compute_pairs(families)
    neighbors = compute_top_k_neighbors(families, pairs, top_k=TOP_K)

    classified = []
    buckets: dict[str, list[float]] = {"mesmo_processo": [], "mesmo_tema": [], "temas_diferentes": []}
    for pair in pairs:
        bucket = bucket_for(pair["family_a"], pair["family_b"])
        classification = classify(pair["score"])
        buckets[bucket].append(pair["score"])
        classified.append(
            {
                **pair,
                "bucket": bucket,
                "classification": classification,
                "is_known_positive_pair": frozenset({pair["family_a"], pair["family_b"]}) == KNOWN_POSITIVE_PAIR,
                "is_known_control_pair": frozenset({pair["family_a"], pair["family_b"]}) == KNOWN_CONTROL_PAIR,
            }
        )

    counts_by_classification = {
        "sem_relacao": sum(1 for p in classified if p["classification"] == "sem_relacao"),
        "similar_a": sum(1 for p in classified if p["classification"] == "similar_a"),
        "sugestao_fusao": sum(1 for p in classified if p["classification"] == "sugestao_fusao"),
    }

    known_positive = next(p for p in classified if p["is_known_positive_pair"])
    known_control = next(p for p in classified if p["is_known_control_pair"])
    max_score_distinct_families = pairs[0]["score"]

    report = {
        "limiar_relacao": LIMIAR_RELACAO,
        "limiar_fusao": LIMIAR_FUSAO,
        "top_k": TOP_K,
        "n_pairs": len(pairs),
        "counts_by_classification": counts_by_classification,
        "known_positive_pair": {
            "families": sorted(KNOWN_POSITIVE_PAIR),
            "score": known_positive["score"],
            "classification": known_positive["classification"],
            "bucket": known_positive["bucket"],
        },
        "known_control_pair": {
            "families": sorted(KNOWN_CONTROL_PAIR),
            "score": known_control["score"],
            "classification": known_control["classification"],
            "bucket": known_control["bucket"],
            "note": "par de controle 'sem relacao conhecida' (dois autos de infracao, casos distintos); "
            "achado da issue #61 -- score ACIMA do par positivo conhecido -- reproduzido aqui com os "
            "embeddings reais (ver README).",
        },
        "max_score_between_distinct_families": max_score_distinct_families,
        "distribution_by_bucket": {bucket: _describe(scores) for bucket, scores in buckets.items()},
        "pairs": classified,
        "top_k_neighbors": neighbors,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Classificacao escrita em {OUTPUT_PATH}\n")
    print(f"limiar_relacao={LIMIAR_RELACAO}  limiar_fusao={LIMIAR_FUSAO}  top_k={TOP_K}")
    print(f"sem_relacao={counts_by_classification['sem_relacao']} "
          f"similar_a={counts_by_classification['similar_a']} "
          f"sugestao_fusao={counts_by_classification['sugestao_fusao']}")
    print(f"\npar positivo conhecido (recurso x complementacao Coelba): "
          f"score={known_positive['score']:.4f}  classificacao={known_positive['classification']}")
    print(f"par de controle (auto x auto, casos nao relacionados): "
          f"score={known_control['score']:.4f}  classificacao={known_control['classification']}")
    print(f"\nmaior score entre quaisquer duas familias distintas: {max_score_distinct_families:.4f}")
    print("\nDistribuicao por bucket (mesmo_processo / mesmo_tema / temas_diferentes):")
    for bucket, stats in report["distribution_by_bucket"].items():
        if stats["n"] == 0:
            print(f"  {bucket}: n=0")
            continue
        print(
            f"  {bucket}: n={stats['n']} min={stats['min']:.4f} "
            f"max={stats['max']:.4f} mean={stats['mean']:.4f} median={stats['median']:.4f}"
        )


if __name__ == "__main__":
    main()
