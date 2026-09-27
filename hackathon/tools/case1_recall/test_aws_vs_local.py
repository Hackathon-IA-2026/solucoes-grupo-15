"""Testes da comparacao TB1 AWS x local (issue #105) contra o
``output/results.json`` commitado - sem rede, sem AWS.

Rodar com: python3.12 -m pytest hackathon/tools/case1_recall/test_aws_vs_local.py -q
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from aws_vs_local import build_search_request, compare_aws_to_local, parse_config

_RESULTS_PATH = Path(__file__).resolve().parent / "output" / "results.json"

GENERATED_AT = "2026-09-27T12:00:00+00:00"


@pytest.fixture()
def baseline() -> dict:
    return json.loads(_RESULTS_PATH.read_text(encoding="utf-8"))


def _result(document_version: str, family_id: str, processo: str, score: float, chunk_index: int):
    return {
        "family_id": family_id,
        "document_version": document_version,
        "excerpt": "...",
        "score": score,
        "localizador": None,
        "document_type": "auto_de_infracao",
        "document_id": "AI",
        "processo_numero": processo,
        "version_date": "2020-01-01",
        "chunk_index": chunk_index,
    }


@pytest.fixture()
def identical_envelope() -> dict:
    """Envelope de POST /v1/search com o mesmo top 3 da baseline commitada
    (literais copiados de results.json#after_index)."""
    return {
        "request_id": "11111111-2222-3333-4444-555555555555",
        "data_mode": "real",
        "corpus_version": "case1-real-v1",
        "model_version": "amazon.titan-embed-text-v2-us-east-1-1024d-normalized",
        "ranking_version": "demo-ranking-v1",
        "results": [
            _result(
                "case1-cemig-auto-2020", "case1-cemig-auto", "48500.000639/2019-07", 1.3751076, 0
            ),
            _result(
                "case1-cemig-recurso-2020",
                "case1-cemig-recurso",
                "48500.000639/2019-07",
                1.3686106,
                1,
            ),
            _result(
                "case1-enel-auto-2018", "case1-enel-auto", "48500.004024/2017-80", 1.3637686, 2
            ),
        ],
        "total": 3,
        "next_cursor": None,
        "stale_corpus": False,
    }


def _criterion(artifact: dict, name: str) -> dict:
    return next(c for c in artifact["gate"]["criteria"] if c["name"] == name)


def test_envelope_identico_aprova(baseline, identical_envelope):
    artifact = compare_aws_to_local(baseline, identical_envelope, generated_at=GENERATED_AT)

    assert artifact["verdict"] == "aprovado"
    assert artifact["gate"]["passed"] is True
    assert all(c["passed"] for c in artifact["gate"]["criteria"])
    assert artifact["informative"]["identical_order"] is True
    assert artifact["informative"]["all_scores_within_tolerance"] is True


def test_posicoes_2_e_3_trocadas_aprova_com_ordem_diferente_no_informativo(
    baseline, identical_envelope
):
    envelope = copy.deepcopy(identical_envelope)
    results = envelope["results"]
    results[1], results[2] = results[2], results[1]

    artifact = compare_aws_to_local(baseline, envelope, generated_at=GENERATED_AT)

    assert artifact["verdict"] == "aprovado"
    assert artifact["informative"]["identical_order"] is False
    assert [h["document_version"] for h in artifact["aws"]["hits"]] == [
        "case1-cemig-auto-2020",
        "case1-enel-auto-2018",
        "case1-cemig-recurso-2020",
    ]
    # 1,3686 x 1,3638: a troca desloca os scores ~0,005, fora da tolerancia
    assert artifact["informative"]["all_scores_within_tolerance"] is False


def test_model_version_diferente_reprova_com_motivo(baseline, identical_envelope):
    envelope = copy.deepcopy(identical_envelope)
    envelope["model_version"] = "amazon.titan-embed-text-v2-us-west-2-1024d-normalized"

    artifact = compare_aws_to_local(baseline, envelope, generated_at=GENERATED_AT)

    assert artifact["verdict"] == "reprovado"
    criterion = _criterion(artifact, "model_version")
    assert criterion["passed"] is False
    assert "us-west-2" in criterion["reason"]
    assert "us-east-1" in criterion["reason"]
    # so esse criterio falhou
    assert [c["name"] for c in artifact["gate"]["criteria"] if not c["passed"]] == ["model_version"]


def test_outro_processo_no_top3_reprova(baseline, identical_envelope):
    envelope = copy.deepcopy(identical_envelope)
    # Recurso Coelba: agrega em 48500.901433/2024-53 (D16), processo que a
    # baseline nao trouxe no top 3.
    envelope["results"][2] = _result(
        "case1-coelba-recurso-2025", "case1-coelba-recurso", "48500.009907/2025-96", 1.36, 2
    )

    artifact = compare_aws_to_local(baseline, envelope, generated_at=GENERATED_AT)

    assert artifact["verdict"] == "reprovado"
    assert artifact["aws"]["processes_retrieved_top3"] == [
        "48500.000639/2019-07",
        "48500.901433/2024-53",
    ]
    criterion = _criterion(artifact, "processes_top3")
    assert criterion["passed"] is False
    assert "48500.901433/2024-53" in criterion["reason"]
    assert "48500.004024/2017-80" in criterion["reason"]


def test_recall_menor_reprova(baseline, identical_envelope):
    envelope = copy.deepcopy(identical_envelope)
    # Top 3 inteiro no mesmo processo agregado -> Recall@3 = 1/3.
    envelope["results"][2] = _result(
        "case1-cemig-decisao-2021", "case1-cemig-decisao", "48500.000639/2019-07", 1.36, 2
    )

    artifact = compare_aws_to_local(baseline, envelope, generated_at=GENERATED_AT)

    assert artifact["verdict"] == "reprovado"
    assert artifact["aws"]["recall_at_3"]["hits_in_golden"] == 1
    assert artifact["aws"]["m5_gate_passed"] is False
    criterion = _criterion(artifact, "recall_at_3")
    assert criterion["passed"] is False
    assert "1/3" in criterion["reason"]
    assert "2/3" in criterion["reason"]


def test_artefato_declara_metrica_identificadores_versoes_e_data(baseline, identical_envelope):
    artifact = compare_aws_to_local(
        baseline,
        identical_envelope,
        generated_at=GENERATED_AT,
        documents_indexed=10,
        base_url="https://d123.cloudfront.net",
    )

    assert artifact["generated_at"] == GENERATED_AT
    assert artifact["metric"]["name"] == "Recall@3"
    assert artifact["metric"]["k"] == 3
    assert artifact["metric"]["denominator"] == 3
    assert "processos agregados" in artifact["metric"]["unit"]
    assert artifact["divergence_explanation"] is None

    local, aws = artifact["local"], artifact["aws"]
    assert local["hits"][0] == {
        "position": 1,
        "document_version": "case1-cemig-auto-2020",
        "processo_canonical": "48500.000639/2019-07",
        "score": 1.3751076,
    }
    assert aws["hits"][2]["position"] == 3
    assert aws["hits"][2]["document_version"] == "case1-enel-auto-2018"
    assert aws["hits"][2]["processo_canonical"] == "48500.004024/2017-80"
    assert aws["hits"][2]["score"] == 1.3637686

    assert local["recall_at_3"]["hits_in_golden"] == 2
    assert aws["recall_at_3"]["denominator"] == 3
    for side in (local, aws):
        assert side["corpus_version"] == "case1-real-v1"
        assert side["model_version"] == "amazon.titan-embed-text-v2-us-east-1-1024d-normalized"
        assert side["ranking_version"] == "demo-ranking-v1"
        assert side["documents_indexed"] == 10
    assert aws["request_id"] == "11111111-2222-3333-4444-555555555555"
    assert aws["base_url"] == "https://d123.cloudfront.net"
    json.dumps(artifact)  # serializavel


def test_script_le_url_e_token_do_ambiente():
    config = parse_config(
        [], {"CAPIWATT_BASE_URL": "https://d123.cloudfront.net/", "CAPIWATT_TOKEN": "tok"}
    )

    assert config.base_url == "https://d123.cloudfront.net"
    assert config.token == "tok"


def test_argumento_prevalece_sobre_ambiente_e_token_e_opcional():
    config = parse_config(
        ["--base-url", "http://localhost:8000", "--output", "/tmp/x.json"],
        {"CAPIWATT_BASE_URL": "https://d123.cloudfront.net"},
    )

    assert config.base_url == "http://localhost:8000"
    assert config.token is None
    assert str(config.output) == "/tmp/x.json"


def test_script_sem_url_base_falha():
    with pytest.raises(SystemExit):
        parse_config([], {})


def test_requisicao_de_busca_usa_pergunta_do_caso1_top3_e_bearer_opcional():
    with_token = build_search_request("https://d123.cloudfront.net", "tok")
    without_token = build_search_request("http://localhost:8000", None)

    assert with_token.full_url == "https://d123.cloudfront.net/v1/search"
    assert with_token.get_method() == "POST"
    assert with_token.get_header("Authorization") == "Bearer tok"
    body = json.loads(with_token.data)
    assert body["query"] == (
        "procure precedentes sobre fiscalização de atendimento a solicitações de conexão de MMGD"
    )
    assert body["top_k"] == 3
    assert without_token.get_header("Authorization") is None
