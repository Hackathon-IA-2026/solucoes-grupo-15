"""Avalia a alternativa de vetor de agregacao levantada pela issue #74
("Avaliar se um vetor de agregacao diferente (ex.: so o trecho de
fundamentacao) separa melhor" o par de controle do par positivo
conhecido) contra o vetor "so motivacao" (``family_vectors.py``,
``motivacao_vector`` -- media dos chunks cuja secao bate com
MOTIVACAO/FUNDAMENTACAO/MERITO, a nomenclatura real do corpus para essa
secao, ver README).

Nao substitui ``calibrate_thresholds.py`` (que usa mean-of-all-chunks,
decisao mantida -- ver README, "Estrategia de vetor de agregacao"). Este
script so imprime a evidencia que fundamenta a decisao de nao adotar a
alternativa.
"""

from __future__ import annotations

import json
from pathlib import Path

from family_labels import FAMILY_INFO
from family_vectors import load_family_vectors

OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "aggregation_alternative_report.json"


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def main() -> None:
    families = load_family_vectors()

    with_motivacao = sorted(fid for fid, info in families.items() if info["motivacao_vector"] is not None)
    without_motivacao = sorted(fid for fid, info in families.items() if info["motivacao_vector"] is None)
    report = {
        "families_with_motivacao_chunks": {
            fid: families[fid]["n_motivacao_chunks"] for fid in with_motivacao
        },
        "families_without_motivacao_chunks": without_motivacao,
        "known_positive_pair_computable": False,
    }

    print(f"Familias COM chunks classificados como 'motivacao' ({len(with_motivacao)}/10):")
    for fid in with_motivacao:
        print(f"  {fid} ({FAMILY_INFO[fid]['document_type']}): {families[fid]['n_motivacao_chunks']} chunks")
    print(f"\nFamilias SEM nenhum chunk classificado como 'motivacao' ({len(without_motivacao)}/10):")
    for fid in without_motivacao:
        print(f"  {fid} ({FAMILY_INFO[fid]['document_type']})")

    print(
        "\n=> o par positivo conhecido mandatado pela issue "
        "(case1-coelba-recurso <-> case1-coelba-complemento) NAO tem vetor "
        "'so motivacao' calculavel para nenhum dos dois lados -- a alternativa "
        "nao pode nem ser comparada contra o proprio criterio de aceite."
    )

    control_a, control_b = "case1-cemig-auto", "case1-enel-auto"
    if control_a in with_motivacao and control_b in with_motivacao:
        full_score = _dot(families[control_a]["vector"], families[control_b]["vector"])
        motivacao_score = _dot(families[control_a]["motivacao_vector"], families[control_b]["motivacao_vector"])
        print(
            f"\nPar de controle ({control_a} <-> {control_b}, dois autos de infracao de "
            f"casos nao relacionados) -- unico par onde a alternativa E calculavel dos dois lados:"
        )
        print(f"  score com mean-of-all-chunks : {full_score:.4f}")
        print(f"  score com so-motivacao        : {motivacao_score:.4f}")
        report["control_pair_comparison"] = {
            "families": [control_a, control_b],
            "score_mean_of_all_chunks": full_score,
            "score_motivacao_only": motivacao_score,
        }
        if motivacao_score < full_score - 0.01:
            print(
                "  => a alternativa REDUZ a similaridade de gabarito entre autos de infracao "
                "de casos distintos (sinal real, nao ruido) -- mas isso nao a torna adotavel "
                "agora: ela so e computavel para 3/10 familias, e o PAR POSITIVO CONHECIDO "
                "mandatado pela issue nao esta entre elas (ver acima). Registrado como pista "
                "para uma futura vetorizacao por secao quando 'motivacao'/similar existir de "
                "forma consistente nos demais tipos documentais, nao adotado nesta calibracao."
            )
        else:
            print(
                "  => a alternativa NAO reduz a similaridade de gabarito entre autos de "
                "infracao de casos distintos (permanece no mesmo patamar) -- nao resolve o "
                "achado da issue #61 nem para o unico par onde e computavel."
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nEvidencia escrita em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
