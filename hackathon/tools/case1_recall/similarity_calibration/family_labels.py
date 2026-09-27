"""Metadados legiveis das 10 familias do corpus real do caso 1, so para
relatorio/leitura humana e para os buckets de comparacao deste script --
nunca alimenta a similaridade em si.

Reindexado a partir de ``hackathon/tools/prototypes/family_similarity/family_labels.py``
(issue #61, chaveado pelo ``document_id`` do protototipo) para as chaves
``family_id`` reais que o servico ``ai`` grava (``case1-<agente>-<tipo>``,
ver ``hackathon/backend/app/fixtures/case1_loader.py`` e
``hackathon/tools/case1_recall/process_aggregation.py``). Mesmos fatos,
mesma fonte (``hackathon/data/case-1-carolina-mmgd/README.md``,
``concerns/d3-data-selection.md``/``concerns/d4-data-dictionary.md``).

``process_group`` usa a mesma agregacao de processo da avaliacao de
Recall@3 (D16, ``process_aggregation.py``): o recurso Coelba
(48500.009907/2025-96) e sua complementacao (48500.017555/2025-42) sao o
mesmo caso Coelba/AI 0035/2025-SFT que 48500.901433/2024-53, nunca
processos independentes.
"""

from __future__ import annotations

FAMILY_INFO: dict[str, dict[str, str]] = {
    "case1-cemig-auto": {
        "document_type": "auto_de_infracao",
        "official_id": "AI 0017/2020-SFE",
        "agent": "Cemig Distribuição S/A",
        "process_group": "48500.000639/2019-07",
    },
    "case1-cemig-recurso": {
        "document_type": "recurso_administrativo",
        "official_id": "recurso em face do AI 0017/2020-SFE",
        "agent": "Cemig Distribuição S/A",
        "process_group": "48500.000639/2019-07",
    },
    "case1-cemig-voto": {
        "document_type": "voto",
        "official_id": "voto, 18ª Reunião Pública Ordinária",
        "agent": "Cemig Distribuição S/A",
        "process_group": "48500.000639/2019-07",
    },
    "case1-enel-auto": {
        "document_type": "auto_de_infracao",
        "official_id": "AI 0032/2018-SFE",
        "agent": "Enel Distribuição Ceará",
        "process_group": "48500.004024/2017-80",
    },
    "case1-enel-recurso": {
        "document_type": "recurso_administrativo",
        "official_id": "recurso ao AI 0032/2018-SFE (carta 011-RB-2019)",
        "agent": "Enel Distribuição Ceará",
        "process_group": "48500.004024/2017-80",
    },
    "case1-enel-voto": {
        "document_type": "voto",
        "official_id": "voto, processo 48500.004024/2017-80",
        "agent": "Enel Distribuição Ceará",
        "process_group": "48500.004024/2017-80",
    },
    "case1-coelba-auto": {
        "document_type": "exposicao_de_motivos",
        "official_id": "exposição de motivos, termo de notificação 0111/2024-SFT",
        "agent": "Neoenergia Coelba",
        "process_group": "48500.901433/2024-53 (Coelba/AI 0035/2025-SFT)",
    },
    "case1-coelba-voto": {
        "document_type": "voto",
        "official_id": "voto, AI 35/2025",
        "agent": "Neoenergia Coelba",
        "process_group": "48500.901433/2024-53 (Coelba/AI 0035/2025-SFT)",
    },
    "case1-coelba-recurso": {
        "document_type": "recurso_administrativo",
        "official_id": "recurso ao AI 0035/2025-SFT",
        "agent": "Neoenergia Coelba",
        "process_group": "48500.901433/2024-53 (Coelba/AI 0035/2025-SFT)",
    },
    "case1-coelba-complemento": {
        "document_type": "complementacao_de_recurso",
        "official_id": "complementação do recurso ao AI 0035/2025-SFT",
        "agent": "Neoenergia Coelba",
        "process_group": "48500.901433/2024-53 (Coelba/AI 0035/2025-SFT)",
    },
}
