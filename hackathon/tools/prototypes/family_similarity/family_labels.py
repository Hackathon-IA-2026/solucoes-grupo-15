"""Human-readable metadata about the 10 famílias of the real corpus, used
only for reporting/calibration reasoning in this prototype -- never fed into
the similarity computation itself.

Source: `hackathon/data/case-1-carolina-mmgd/README.md` (inventário) and
`concerns/d3-data-selection.md` / `concerns/d4-data-dictionary.md` (tipos
documentais e identidade de família). Verified against the actual .md
extractions in `hackathon/data/case-1-carolina-mmgd/` before being used to
pick calibration pairs (see README.md, "Verificação dos pares conhecidos").
"""

from __future__ import annotations

FAMILY_INFO: dict[str, dict[str, str]] = {
    "48500.000639-2019-07/auto-infracao-48500.000639-2019-07": {
        "document_type": "auto_de_infracao",
        "official_id": "AI 0017/2020-SFE",
        "agent": "Cemig Distribuição S/A",
        "process_group": "48500.000639/2019-07",
    },
    "48500.000639-2019-07/recurso-48500.000639-2019-07": {
        "document_type": "recurso_administrativo",
        "official_id": "recurso em face do AI 0017/2020-SFE",
        "agent": "Cemig Distribuição S/A",
        "process_group": "48500.000639/2019-07",
    },
    "48500.000639-2019-07/voto-48500.000639-2019-07": {
        "document_type": "voto",
        "official_id": "voto, 18ª Reunião Pública Ordinária",
        "agent": "Cemig Distribuição S/A",
        "process_group": "48500.000639/2019-07",
    },
    "48500.004024-2017-80/auto-infracao-48500.004024-2017-80": {
        "document_type": "auto_de_infracao",
        "official_id": "AI 0032/2018-SFE",
        "agent": "Enel Distribuição Ceará",
        "process_group": "48500.004024/2017-80",
    },
    "48500.004024-2017-80/recurso-48500.004024-2017-80": {
        "document_type": "recurso_administrativo",
        "official_id": "recurso ao AI 0032/2018-SFE (carta 011-RB-2019)",
        "agent": "Enel Distribuição Ceará",
        "process_group": "48500.004024/2017-80",
    },
    "48500.004024-2017-80/voto-48500.004024-2017-80": {
        "document_type": "voto",
        "official_id": "voto, processo 48500.004024/2017-80",
        "agent": "Enel Distribuição Ceará",
        "process_group": "48500.004024/2017-80",
    },
    "48500.009907-2025-96/recurso-48500.009907-2025-96": {
        "document_type": "recurso_administrativo",
        "official_id": "recurso ao AI 0035/2025-SFT",
        "agent": "Neoenergia Coelba",
        "process_group": "48500.901433/2024-53 (Coelba/AI 0035/2025-SFT)",
    },
    "48500.017555-2025-42/complementacao-recurso-48500.017555-2025-42": {
        "document_type": "complementacao_de_recurso",
        "official_id": "complementação do recurso ao AI 0035/2025-SFT",
        "agent": "Neoenergia Coelba",
        "process_group": "48500.901433/2024-53 (Coelba/AI 0035/2025-SFT)",
    },
    "48500.901433-2024-53/auto-infracao-48500.901433-2024-53": {
        "document_type": "exposicao_de_motivos",
        "official_id": "exposição de motivos, termo de notificação 0111/2024-SFT",
        "agent": "Neoenergia Coelba",
        "process_group": "48500.901433/2024-53 (Coelba/AI 0035/2025-SFT)",
    },
    "48500.901433-2024-53/voto-48500.901433-2024-53": {
        "document_type": "voto",
        "official_id": "voto, AI 35/2025",
        "agent": "Neoenergia Coelba",
        "process_group": "48500.901433/2024-53 (Coelba/AI 0035/2025-SFT)",
    },
}
