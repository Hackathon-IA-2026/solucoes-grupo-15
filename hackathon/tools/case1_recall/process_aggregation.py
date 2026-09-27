"""Agregacao de processo (D16) para a medicao de Recall@3 real (issue #69).

Porta a mesma regra de agregacao do protototipo do Recall@3 (issue #60,
`hackathon/tools/prototypes/recall_baseline/process_map.py`), so que
chaveada por ``processo_numero`` (notacao com barra, ja normalizada
pelo catalogo - ver app/fixtures/case1_loader.py) em vez do nome da
pasta do corpus. Fonte: `hackathon/data/case-1-carolina-mmgd/README.md`
e `requirements/perspec-me/capiwatt-lens-hackathon/concerns/d16-golden-dataset.md`.

O corpus tem 5 NUPs distintos, mas so 3 *processos agregados* para fins
de avaliacao: o recurso Coelba (`48500.009907/2025-96`) e sua
complementacao (`48500.017555/2025-42`) sao o mesmo caso Coelba/AI
`0035/2025-SFT` que `48500.901433/2024-53` e devem ser agregados nele,
nunca contados como processos independentes.

Esta agregacao e logica de AVALIACAO (Recall@3 do gabarito D16), nunca
parte do port VectorService - o ai/backend nunca precisam dela em
produção, so o script que mede a metrica (ver seed_and_measure.py).
"""

from __future__ import annotations

# processo_numero (como o catalogo grava, notacao com barra) -> processo
# agregado canonico (mesma notacao) para fins de avaliacao D16.
RAW_TO_CANONICAL_PROCESS: dict[str, str] = {
    "48500.004024/2017-80": "48500.004024/2017-80",
    "48500.000639/2019-07": "48500.000639/2019-07",
    "48500.901433/2024-53": "48500.901433/2024-53",
    # Mesmo caso Coelba/AI 0035/2025-SFT que 48500.901433/2024-53 - agregados,
    # nunca processos independentes (D16, "Confirmed facts").
    "48500.009907/2025-96": "48500.901433/2024-53",
    "48500.017555/2025-42": "48500.901433/2024-53",
}

GOLDEN_TOP3_PROCESSES: frozenset[str] = frozenset(
    {
        "48500.004024/2017-80",
        "48500.000639/2019-07",
        "48500.901433/2024-53",
    }
)


def canonical_process_for(processo_numero: str) -> str:
    try:
        return RAW_TO_CANONICAL_PROCESS[processo_numero]
    except KeyError as exc:
        raise KeyError(
            f"processo_numero desconhecido, sem mapeamento de agregacao: {processo_numero!r}"
        ) from exc
