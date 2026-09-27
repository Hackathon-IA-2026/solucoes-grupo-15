"""Comparacao TB1 AWS x local (issue #105, decisao em
`requirements/perspec-me/capiwatt-aws-deploy/topics/topic-tb1-aws-vs-local.md`).

Repete a pergunta com gabarito do caso 1 (``TEST_QUESTION``, ``top_k=3``)
contra ``POST /v1/search`` de uma URL base configuravel (CloudFront na
AWS, ou o Compose local com ``AUTH_MODE=none`` para validar antes do
deploy) e compara o envelope com a baseline local commitada
(``output/results.json``). O lado local NUNCA e reexecutado.

Gate de equivalencia (todos precisam valer):
  - ``corpus_version``, ``model_version`` e ``ranking_version`` iguais aos
    da baseline;
  - o mesmo conjunto de processos agregados distintos no top 3 (mesma
    agregacao D16 de process_aggregation.py);
  - o mesmo ``Recall@3`` da baseline (2/3) e o gate de M5 aprovado.

Informativo, fora do gate: ordem identica dos hits e |Δscore| <= 0,001
por posicao (HNSW e aproximado; paridade bit a bit nao e requisito, I7).

``compare_aws_to_local`` e a funcao pura (baseline + envelope -> artefato,
testada em test_aws_vs_local.py sem rede). ``main`` e o script: faz a
chamada HTTP e grava o artefato.

Uso:
    CAPIWATT_BASE_URL=https://dxxxx.cloudfront.net CAPIWATT_TOKEN=<access token> \\
        python3.12 hackathon/tools/case1_recall/aws_vs_local.py
    # ou, contra o Compose local (AUTH_MODE=none, sem token), sem sobrescrever
    # o artefato commitado:
    python3.12 hackathon/tools/case1_recall/aws_vs_local.py \\
        --base-url http://localhost:8000 --output /tmp/aws_vs_local.local.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS_DIR))

from process_aggregation import (  # noqa: E402
    GOLDEN_TOP3_PROCESSES,
    RAW_TO_CANONICAL_PROCESS,
)

# Mesmos valores de seed_and_measure.py (a baseline foi medida com eles).
# Duplicados aqui porque seed_and_measure.py importa o backend no topo do
# modulo - este script so fala HTTP e nao deve depender do backend.
TEST_QUESTION = (
    "procure precedentes sobre fiscalização de atendimento a solicitações de conexão de MMGD"
)
TOP_K = 3

# results.json foi medido direto no ai (AiClient.search), antes de existir
# ranking_version no caminho medido - o campo nao esta na baseline. A busca
# publica com o mesmo corpus/modelo declara esta constante
# (backend/app/routes/search.py::RANKING_VERSION, e
# output/backend_search_envelope_sample.json), entao ela e a
# ranking_version da baseline. Se results.json passar a declarar a sua, ela
# prevalece.
BASELINE_RANKING_VERSION = "demo-ranking-v1"

# Execucao da baseline usada na comparacao. As tres execucoes de
# results.json (index, reindex via ai, reindex dos vetores brutos) tem o
# mesmo top 3; after_index e a primeira.
BASELINE_MEASUREMENT = "after_index"

SCORE_TOLERANCE = 0.001

# Gate de M5 (capiwatt-lens-hackathon/concerns/m5-performance-metrics.md):
# Recall@3 >= 2/3, em processos agregados do gabarito.
M5_GATE_HITS_IN_GOLDEN = 2

OUTPUT_PATH = _TOOLS_DIR / "output" / "aws_vs_local.json"


def _canonical_process(processo_numero: str | None) -> str | None:
    # Processo fora do mapeamento D16 fica com o numero cru: nao e do
    # gabarito, mas precisa aparecer no conjunto para reprovar o gate.
    if processo_numero is None:
        return None
    return RAW_TO_CANONICAL_PROCESS.get(processo_numero, processo_numero)


def _side(hits: list[dict]) -> dict:
    """Hits por posicao + processos distintos + Recall@3 de um lado."""
    positioned = [
        {
            "position": index + 1,
            "document_version": hit["document_version"],
            "processo_canonical": hit["processo_canonical"],
            "score": hit["score"],
        }
        for index, hit in enumerate(hits[:TOP_K])
    ]
    processes: list[str] = []
    for hit in positioned:
        processo = hit["processo_canonical"]
        if processo and processo not in processes:
            processes.append(processo)
    hits_in_golden = sorted(set(processes) & GOLDEN_TOP3_PROCESSES)
    denominator = len(GOLDEN_TOP3_PROCESSES)
    return {
        "hits": positioned,
        "processes_retrieved_top3": processes,
        "recall_at_3": {
            "hits_in_golden": len(hits_in_golden),
            "denominator": denominator,
            "value": len(hits_in_golden) / denominator,
            "processes_in_golden": hits_in_golden,
        },
        "m5_gate_passed": len(hits_in_golden) >= M5_GATE_HITS_IN_GOLDEN,
    }


def _local_side(baseline: dict) -> dict:
    measurement = baseline[BASELINE_MEASUREMENT]
    hits = [
        {
            "document_version": hit["document_version"],
            "processo_canonical": hit["processo_canonical"],
            "score": hit["score"],
        }
        for hit in measurement["hits"]
    ]
    return {
        "source": f"hackathon/tools/case1_recall/output/results.json#{BASELINE_MEASUREMENT}",
        "corpus_version": baseline["corpus_version"],
        "model_version": measurement["model_version"],
        "ranking_version": baseline.get("ranking_version", BASELINE_RANKING_VERSION),
        "documents_indexed": baseline["documents_indexed"],
        **_side(hits),
    }


def _aws_side(envelope: dict, *, documents_indexed: int | None, base_url: str | None) -> dict:
    hits = [
        {
            "document_version": result["document_version"],
            "processo_canonical": _canonical_process(result.get("processo_numero")),
            "score": result["score"],
        }
        for result in envelope["results"]
    ]
    return {
        "base_url": base_url,
        "request_id": envelope["request_id"],
        "data_mode": envelope.get("data_mode"),
        "corpus_version": envelope["corpus_version"],
        "model_version": envelope["model_version"],
        "ranking_version": envelope["ranking_version"],
        # O envelope de /v1/search nao traz documents_indexed; vem do
        # relatorio do seed (argumento do script). None = nao informado.
        "documents_indexed": documents_indexed,
        **_side(hits),
    }


def _gate_criteria(local: dict, aws: dict) -> list[dict]:
    criteria = []
    for field in ("corpus_version", "model_version", "ranking_version"):
        passed = local[field] == aws[field]
        criteria.append(
            {
                "name": field,
                "passed": passed,
                "reason": (
                    f"igual a baseline ({local[field]!r})"
                    if passed
                    else f"AWS {aws[field]!r} != baseline {local[field]!r}"
                ),
            }
        )

    local_set = set(local["processes_retrieved_top3"])
    aws_set = set(aws["processes_retrieved_top3"])
    passed = local_set == aws_set
    criteria.append(
        {
            "name": "processes_top3",
            "passed": passed,
            "reason": (
                f"mesmo conjunto de processos agregados no top {TOP_K}: {sorted(local_set)}"
                if passed
                else (
                    f"conjunto diferente: so na AWS {sorted(aws_set - local_set)}, "
                    f"so na baseline {sorted(local_set - aws_set)}"
                )
            ),
        }
    )

    local_recall = local["recall_at_3"]
    aws_recall = aws["recall_at_3"]
    local_fraction = f"{local_recall['hits_in_golden']}/{local_recall['denominator']}"
    aws_fraction = f"{aws_recall['hits_in_golden']}/{aws_recall['denominator']}"
    same_recall = (
        local_recall["hits_in_golden"] == aws_recall["hits_in_golden"]
        and local_recall["denominator"] == aws_recall["denominator"]
    )
    passed = same_recall and aws["m5_gate_passed"]
    if passed:
        reason = f"Recall@3 = {aws_fraction}, igual a baseline, gate M5 (>= 2/3) aprovado"
    elif not same_recall:
        reason = f"Recall@3 AWS {aws_fraction} != baseline {local_fraction}"
    else:
        reason = f"Recall@3 AWS {aws_fraction} abaixo do gate M5 (>= 2/3)"
    criteria.append({"name": "recall_at_3", "passed": passed, "reason": reason})
    return criteria


def _informative(local: dict, aws: dict) -> dict:
    local_hits = local["hits"]
    aws_hits = aws["hits"]
    identical_order = [h["document_version"] for h in local_hits] == [
        h["document_version"] for h in aws_hits
    ]
    score_deltas = []
    for local_hit, aws_hit in zip(local_hits, aws_hits, strict=False):
        abs_delta = abs(local_hit["score"] - aws_hit["score"])
        score_deltas.append(
            {
                "position": local_hit["position"],
                "local_score": local_hit["score"],
                "aws_score": aws_hit["score"],
                "abs_delta": abs_delta,
                "within_tolerance": abs_delta <= SCORE_TOLERANCE,
            }
        )
    return {
        "identical_order": identical_order,
        "score_tolerance": SCORE_TOLERANCE,
        "score_deltas": score_deltas,
        "all_scores_within_tolerance": len(local_hits) == len(aws_hits)
        and all(d["within_tolerance"] for d in score_deltas),
    }


def compare_aws_to_local(
    baseline: dict,
    envelope: dict,
    *,
    generated_at: str,
    documents_indexed: int | None = None,
    base_url: str | None = None,
) -> dict:
    """Baseline (results.json) + envelope de POST /v1/search -> artefato
    aws_vs_local.json. Pura: sem rede, sem relogio, sem disco."""
    local = _local_side(baseline)
    aws = _aws_side(envelope, documents_indexed=documents_indexed, base_url=base_url)
    criteria = _gate_criteria(local, aws)
    gate_passed = all(c["passed"] for c in criteria)
    return {
        "generated_at": generated_at,
        "query": baseline["query"],
        "metric": {
            "name": "Recall@3",
            "unit": "processos agregados do gabarito (D16) recuperados no top-k",
            "k": TOP_K,
            "denominator": len(GOLDEN_TOP3_PROCESSES),
            "golden_top3_processes": sorted(GOLDEN_TOP3_PROCESSES),
            "m5_gate": f">= {M5_GATE_HITS_IN_GOLDEN}/{len(GOLDEN_TOP3_PROCESSES)}",
        },
        "local": local,
        "aws": aws,
        "gate": {"passed": gate_passed, "criteria": criteria},
        "informative": _informative(local, aws),
        "verdict": "aprovado" if gate_passed else "reprovado",
        # Preenchido a mao quando o veredito for "reprovado": o M4 so sai com
        # o gate aprovado ou com a divergencia explicada (topic-tb1-aws-vs-local).
        "divergence_explanation": None,
    }


# ---------------------------------------------------------------------------
# Script (rede e disco ficam so daqui para baixo)
# ---------------------------------------------------------------------------


class Config(argparse.Namespace):
    base_url: str
    token: str | None
    output: Path
    baseline: Path
    documents_indexed: int | None


def parse_config(argv: list[str], environ: dict[str, str]) -> Config:
    """Argumento prevalece sobre variavel de ambiente; token e opcional
    (o Compose local roda com AUTH_MODE=none)."""
    parser = argparse.ArgumentParser(description="Compara o TB1 na AWS com a baseline local.")
    parser.add_argument(
        "--base-url",
        default=environ.get("CAPIWATT_BASE_URL"),
        help="URL base da API (ex.: https://dxxxx.cloudfront.net); env CAPIWATT_BASE_URL",
    )
    parser.add_argument(
        "--token",
        default=environ.get("CAPIWATT_TOKEN"),
        help="access token Cognito, enviado como Bearer; env CAPIWATT_TOKEN",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--baseline", type=Path, default=_TOOLS_DIR / "output" / "results.json")
    parser.add_argument(
        "--documents-indexed",
        type=int,
        default=int(environ["CAPIWATT_DOCUMENTS_INDEXED"])
        if environ.get("CAPIWATT_DOCUMENTS_INDEXED")
        else None,
        help="documents_indexed do seed na AWS (o envelope nao traz); "
        "env CAPIWATT_DOCUMENTS_INDEXED",
    )
    config = parser.parse_args(argv, namespace=Config())
    if not config.base_url:
        parser.error("URL base obrigatoria: --base-url ou CAPIWATT_BASE_URL")
    config.base_url = config.base_url.rstrip("/")
    config.token = config.token or None
    return config


def build_search_request(base_url: str, token: str | None) -> urllib.request.Request:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(
        f"{base_url}/v1/search",
        data=json.dumps({"query": TEST_QUESTION, "top_k": TOP_K}).encode("utf-8"),
        headers=headers,
        method="POST",
    )


def main(argv: list[str] | None = None) -> int:
    config = parse_config(sys.argv[1:] if argv is None else argv, dict(os.environ))
    baseline = json.loads(config.baseline.read_text(encoding="utf-8"))

    try:
        with urllib.request.urlopen(
            build_search_request(config.base_url, config.token), timeout=60
        ) as resp:
            envelope = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"ERRO: POST {config.base_url}/v1/search -> HTTP {exc.code}", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"ERRO: POST {config.base_url}/v1/search -> {exc.reason}", file=sys.stderr)
        return 2

    artifact = compare_aws_to_local(
        baseline,
        envelope,
        generated_at=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        documents_indexed=config.documents_indexed,
        base_url=config.base_url,
    )
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"request_id AWS: {artifact['aws']['request_id']}")
    for criterion in artifact["gate"]["criteria"]:
        status = "ok" if criterion["passed"] else "FALHOU"
        print(f"  [{status}] {criterion['name']}: {criterion['reason']}")
    info = artifact["informative"]
    print(
        f"  (informativo) ordem identica={info['identical_order']} "
        f"|Δscore|<={SCORE_TOLERANCE}={info['all_scores_within_tolerance']}"
    )
    print(f"Veredito: {artifact['verdict']} -> {config.output}")
    return 0 if artifact["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
