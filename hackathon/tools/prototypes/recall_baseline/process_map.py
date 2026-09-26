"""Process (NUP) normalization and the D16 golden dataset for issue #60.

Source: `hackathon/data/case-1-carolina-mmgd/README.md` and
`requirements/perspec-me/capiwatt-lens-hackathon/concerns/d16-golden-dataset.md`.

The corpus has 5 folders (one per NUP as filed), but only 3 *processos
agregados* for evaluation purposes: the Coelba recurso
(`48500.009907/2025-96`) and its complementação (`48500.017555/2025-42`)
belong to the same Coelba/AI `0035/2025-SFT` case as
`48500.901433/2024-53` and must be aggregated into it, not counted as
independent processes.
"""

from __future__ import annotations

# Folder name (as it appears under hackathon/data/case-1-carolina-mmgd/) ->
# canonical NUP (slash notation, as Carolina's Top 3 and D16 write it).
FOLDER_TO_CANONICAL_PROCESS: dict[str, str] = {
    "48500.004024-2017-80": "48500.004024/2017-80",
    "48500.000639-2019-07": "48500.000639/2019-07",
    "48500.901433-2024-53": "48500.901433/2024-53",
    # Same Coelba/AI 0035/2025-SFT case as 48500.901433/2024-53 -- aggregated,
    # not independent processes (D16, "Confirmed facts" + "Derived requirements").
    "48500.009907-2025-96": "48500.901433/2024-53",
    "48500.017555-2025-42": "48500.901433/2024-53",
}

GOLDEN_TOP3_PROCESSES: frozenset[str] = frozenset(
    {
        "48500.004024/2017-80",
        "48500.000639/2019-07",
        "48500.901433/2024-53",
    }
)


def canonical_process_for_folder(folder_name: str) -> str:
    try:
        return FOLDER_TO_CANONICAL_PROCESS[folder_name]
    except KeyError as exc:
        raise KeyError(
            f"Pasta de corpus desconhecida, sem mapeamento de processo: {folder_name!r}"
        ) from exc
