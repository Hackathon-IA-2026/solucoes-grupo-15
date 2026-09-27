"""PROTOTYPE — calibra `limiar_relacao` e `limiar_fusao` (issue #61) contra
os pares conhecidos do corpus real, usando a matriz de similaridade de
`compute_similarity.py`.

Lê `output/family_similarity.json` (gerado por `compute_similarity.py`),
classifica cada um dos 45 pares em `sem_relacao` / `similar_a` / `sugestao_fusao`
segundo os limiares calibrados abaixo, e escreve
`output/calibration_report.json` com a evidência completa. Ver `README.md`
("Calibração") para o raciocínio completo por trás destes dois números.

Valores calibrados (2026-09-26, evidência = este protótipo):
    LIMIAR_RELACAO = 0.80
    LIMIAR_FUSAO   = 0.97
"""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
SIMILARITY_PATH = OUTPUT_DIR / "family_similarity.json"

LIMIAR_RELACAO = 0.80
LIMIAR_FUSAO = 0.97

assert LIMIAR_RELACAO < LIMIAR_FUSAO, "D14 exige limiar_relacao < limiar_fusao"

# Pares conhecidos usados para calibrar (validados contra o texto real dos
# documentos -- ver README.md, "Verificação dos pares conhecidos").
KNOWN_STRONG_RELATION_PAIRS = {
    frozenset(
        {
            "48500.009907-2025-96/recurso-48500.009907-2025-96",
            "48500.017555-2025-42/complementacao-recurso-48500.017555-2025-42",
        }
    ): (
        "complementação cita explicitamente a data e o número do próprio "
        "recurso (RTC-NCLB 022/2025, 20/03/2025) e retoma o mesmo pedido "
        "'ii'; mesmo caso Coelba/AI 0035/2025-SFT, mesma linha "
        "argumentativa; tipos documentais diferentes -> candidato a "
        "similar_a, nunca fusão."
    )
}

# Par hipotetizado no texto da issue como "controle sem relação" (mesmo tipo
# documental, casos totalmente distintos: Enel Ceará vs Cemig). A verificação
# contra os dados reais MOSTROU QUE A HIPÓTESE NÃO SE CONFIRMA (ver
# README.md, "Achado inesperado") -- documentado aqui, não escondido.
HYPOTHESIZED_CONTROL_PAIR = frozenset(
    {
        "48500.000639-2019-07/auto-infracao-48500.000639-2019-07",
        "48500.004024-2017-80/auto-infracao-48500.004024-2017-80",
    }
)


def classify(score: float) -> str:
    if score >= LIMIAR_FUSAO:
        return "sugestao_fusao"
    if score >= LIMIAR_RELACAO:
        return "similar_a"
    return "sem_relacao"


def main() -> None:
    data = json.loads(SIMILARITY_PATH.read_text(encoding="utf-8"))
    pairs = data["all_pairs_sorted_desc"]

    classified = []
    for p in pairs:
        key = frozenset({p["family_a"], p["family_b"]})
        band = classify(p["score"])
        classified.append(
            {
                **p,
                "band": band,
                "is_known_strong_relation_pair": key
                in KNOWN_STRONG_RELATION_PAIRS,
                "is_hypothesized_control_pair": key
                == HYPOTHESIZED_CONTROL_PAIR,
            }
        )

    fusao = [p for p in classified if p["band"] == "sugestao_fusao"]
    similar = [p for p in classified if p["band"] == "similar_a"]
    none_band = [p for p in classified if p["band"] == "sem_relacao"]

    max_distinct_score = max(p["score"] for p in pairs)  # no known duplicate
    known_pair = next(
        p for p in classified if p["is_known_strong_relation_pair"]
    )
    control_pair = next(
        p for p in classified if p["is_hypothesized_control_pair"]
    )

    report = {
        "limiar_relacao": LIMIAR_RELACAO,
        "limiar_fusao": LIMIAR_FUSAO,
        "top_k": data["top_k"],
        "n_pairs_total": len(pairs),
        "n_pairs_sugestao_fusao": len(fusao),
        "n_pairs_similar_a": len(similar),
        "n_pairs_sem_relacao": len(none_band),
        "max_score_among_distinct_families": max_distinct_score,
        "known_strong_relation_pair_result": known_pair,
        "hypothesized_control_pair_result": control_pair,
        "no_true_fusion_candidate_in_corpus": True,
        "pairs": classified,
    }

    out_path = OUTPUT_DIR / "calibration_report.json"
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"limiar_relacao={LIMIAR_RELACAO}  limiar_fusao={LIMIAR_FUSAO}")
    print(
        f"{len(fusao)} sugestao_fusao / {len(similar)} similar_a / "
        f"{len(none_band)} sem_relacao (de {len(pairs)} pares)"
    )
    print(
        f"Maior score entre famílias distintas: {max_distinct_score:.4f} "
        f"(margem até limiar_fusao: {LIMIAR_FUSAO - max_distinct_score:.4f})"
    )
    print()
    print("Par conhecido fortemente relacionado (recurso <-> complementação):")
    print(
        f"  score={known_pair['score']:.4f} -> banda={known_pair['band']!r}"
    )
    print()
    print("Par-hipótese de controle (auto Enel vs auto Cemig, sem relação):")
    print(
        f"  score={control_pair['score']:.4f} -> banda={control_pair['band']!r}"
        f" (esperado 'sem_relacao'; ver README para a discrepância)"
    )
    print()
    print("Pares na banda similar_a:")
    for p in sorted(similar, key=lambda p: p["score"], reverse=True):
        print(f"  {p['score']:.4f}  {p['family_a']}  <->  {p['family_b']}")


if __name__ == "__main__":
    main()
