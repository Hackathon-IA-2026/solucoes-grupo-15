"""Ingestao real + medicao de Recall@3 PELO SERVICO ai (issue #69, estendido
pela #73 com custo/tokens e reindex sem AWS).

Diferenca em relacao ao protototipo do Recall@3 (issue #60,
`hackathon/tools/prototypes/recall_baseline/`): aquele script chamava
Bedrock diretamente e fazia chunking/ranking no proprio script, sem
tocar nenhum codigo de producao. Este script usa o caminho real de
producao ponta a ponta:

    load_case1_real_corpus()          (app/fixtures/case1_loader.py)
      -> run_ingestion(..., ai_client=AiClient real, session=Postgres real)
           -> POST /internal/v1/index no servico ai (chunking.py real +
              embeddings.py real, EMBEDDER=bedrock)
      -> AiClient.search(TEST_QUESTION, top_k=3)
           -> POST /internal/v1/search no servico ai (busca vetorial
              real no OpenSearch, nao mais fixture)
      -> agregacao de processo (D16, process_aggregation.py) e Recall@3

Pre-requisitos (nao providos por este script):
  - Um Postgres acessivel em DATABASE_URL (schema criado via
    Base.metadata.create_all, feito aqui).
  - O servico ai rodando com EMBEDDER=bedrock e acessivel em
    AI_BASE_URL, com OPENSEARCH_URL apontando a um OpenSearch local
    acessivel e credenciais AWS validas no ambiente do PROCESSO DO ai
    (nao deste script - os Passos 1/2 nunca falam com Bedrock/OpenSearch
    diretamente, so HTTP com o ai e SQL com o Postgres). O Passo 3 fala
    com o OpenSearch diretamente (nunca com Bedrock) - ver
    ``OPENSEARCH_URL``/``RAW_VECTORS_PATH`` abaixo.

Uso:
    DATABASE_URL=postgresql+psycopg://... AI_BASE_URL=http://localhost:8001 \\
    OPENSEARCH_URL=http://localhost:9200 \\
        python3.12 hackathon/tools/case1_recall/seed_and_measure.py

Tambem exercita dois ACs da issue #73 sobre o mesmo corpus do caso 1:

- Passo 2 (reindex via ai, issue #69): ``AiClient.reindex`` com o mesmo
  corpus - reconstroi o indice OpenSearch do zero recomputando os
  embeddings (chama Bedrock de novo).
- Passo 3 (reindex a partir dos vetores brutos, issue #73/I7): reconstroi
  o MESMO indice OpenSearch so a partir do arquivo de vetores brutos que
  o ai persistiu durante os Passos 1/2 (``app/raw_vectors.py``) - SEM
  nenhuma chamada Bedrock/AWS desta vez (ver
  ``reindex_from_raw_vectors.py``). Recall@3 identico ao Passo 2 prova
  que o indice foi reconstruido corretamente sem reprocessar nada.

Escreve `output/results.json` (sem embeddings - o indice vetorial e
responsabilidade do ai, este script so guarda o resultado da medicao)
e imprime um resumo legivel no stdout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parents[2]
_BACKEND_DIR = _REPO_ROOT / "hackathon" / "backend"
_REINDEX_FROM_RAW_SCRIPT = _TOOLS_DIR / "reindex_from_raw_vectors.py"
_DEFAULT_RAW_VECTORS_PATH = (
    _REPO_ROOT
    / "hackathon"
    / ".pipeline-output"
    / "documents"
    / "_raw_vectors"
    / "amazon.titan-embed-text-v2-us-east-1-1024d-normalized.jsonl"
)

sys.path.insert(0, str(_TOOLS_DIR))
sys.path.insert(0, str(_BACKEND_DIR))

from process_aggregation import (  # noqa: E402
    GOLDEN_TOP3_PROCESSES,
    canonical_process_for,
)

from app.clients.ai_client import AiClient, IndexDocumentPayload  # noqa: E402
from app.db import Base, make_engine, make_session_factory  # noqa: E402
from app.fixtures.case1_loader import load_case1_real_corpus  # noqa: E402
from app.routes.ingestions import run_ingestion  # noqa: E402

# ai/app e backend/app sao dois pacotes DISTINTOS que por coincidencia se
# chamam "app" - importar os dois no mesmo processo Python colide em
# sys.modules["app"] (o segundo import silenciosamente resolve contra o
# primeiro pacote carregado). Por isso o Passo 3 roda
# reindex_from_raw_vectors.py como subprocesso (so ele importa ai/app),
# nunca por import direto aqui - ver reindex_from_raw_vectors.py, que ja
# fala com o OpenSearch diretamente, sem tocar em nenhum codigo do backend.
_TITAN_V2_PRICING_USD_PER_MILLION_TOKENS = 0.02  # espelha ai/app/embeddings.py::PRICING_USD_PER_MILLION_TOKENS


def _estimate_embedding_cost_usd(input_tokens: int) -> float:
    return (input_tokens / 1_000_000) * _TITAN_V2_PRICING_USD_PER_MILLION_TOKENS


TEST_QUESTION = "procure precedentes sobre fiscalização de atendimento a solicitações de conexão de MMGD"
TOP_K = 3
OUTPUT_DIR = _TOOLS_DIR / "output"


def main() -> int:
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://capiwatt:capiwatt@localhost:5432/capiwatt"
    )
    ai_base_url = os.environ.get("AI_BASE_URL", "http://localhost:8001")

    # Timeout generoso: index/reindex fazem uma chamada Bedrock por chunk,
    # sequencialmente, dentro de uma unica requisicao HTTP (10 documentos,
    # ~300+ chunks no corpus real do caso 1) - o timeout padrao do AiClient
    # (10s) e curto demais para isso.
    ai_client = AiClient(base_url=ai_base_url, timeout=900.0)
    if not ai_client.health():
        print(f"ERRO: servico ai em {ai_base_url} nao respondeu ao health check.", file=sys.stderr)
        return 1

    corpus = load_case1_real_corpus()
    print(f"Corpus real do caso 1: {len(corpus.documents)} documentos, corpus_version={corpus.corpus_version!r}")

    engine = make_engine(database_url)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)

    document_version_to_processo = {doc.document_version: doc.processo_numero for doc in corpus.documents}

    print("\n== Passo 1: index (ingestao real, backend -> ai) ==")
    t0 = time.time()
    with session_factory() as session:
        result = run_ingestion(corpus, ai_client=ai_client, session=session)
        session.commit()
    print(
        f"ingestion_job_id={result.ingestion_job_id} "
        f"families={result.families_count} versions={result.versions_count} "
        f"total_input_tokens={result.total_input_tokens} "
        f"({time.time() - t0:.1f}s)"
    )
    cost_usd = (
        _estimate_embedding_cost_usd(result.total_input_tokens)
        if result.total_input_tokens
        else None
    )
    if cost_usd is not None:
        print(f"custo estimado de embeddings (Titan V2, tabela publica): US${cost_usd:.6f}")

    first_measurement = _measure_recall(ai_client, document_version_to_processo, label="apos index")

    print("\n== Passo 2: reindex via ai (AC #69 'reindex(corpus_version) reconstrói o índice do zero') ==")
    t0 = time.time()
    ai_client.reindex(
        [
            IndexDocumentPayload(
                document_version=doc.document_version,
                text=doc.text,
                family_id=doc.family_id,
                corpus_version=corpus.corpus_version,
            )
            for doc in corpus.documents
        ]
    )
    print(f"reindex via ai concluido em {time.time() - t0:.1f}s (chama Bedrock de novo)")

    second_measurement = _measure_recall(ai_client, document_version_to_processo, label="apos reindex via ai")

    print(
        "\n== Passo 3: reindex a partir dos vetores brutos (issue #73/I7, SEM chamar Bedrock/AWS) =="
    )
    raw_vectors_path = os.environ.get("RAW_VECTORS_PATH", str(_DEFAULT_RAW_VECTORS_PATH))
    opensearch_url = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
    # Subprocesso proposital (ver comentario no topo do arquivo sobre a
    # colisao de nomes ai/app vs backend/app) - a env deste subprocesso
    # NUNCA recebe credenciais AWS (so OPENSEARCH_URL/RAW_VECTORS_PATH),
    # provando que reindex_from_raw_vectors.py reconstroi o indice sem
    # depender delas.
    subprocess_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("AWS_")
    }
    subprocess_env["OPENSEARCH_URL"] = opensearch_url
    subprocess_env["RAW_VECTORS_PATH"] = raw_vectors_path

    t0 = time.time()
    raw_reindex = subprocess.run(
        [sys.executable, str(_REINDEX_FROM_RAW_SCRIPT)],
        env=subprocess_env,
        capture_output=True,
        text=True,
    )
    raw_reindex_elapsed = time.time() - t0
    print(raw_reindex.stdout)
    if raw_reindex.returncode != 0:
        print(raw_reindex.stderr, file=sys.stderr)
        raise RuntimeError("reindex_from_raw_vectors.py falhou (ver stderr acima)")

    third_measurement = _measure_recall(
        ai_client, document_version_to_processo, label="apos reindex a partir dos vetores brutos"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "results.json").write_text(
        json.dumps(
            {
                "query": TEST_QUESTION,
                "corpus_version": corpus.corpus_version,
                "top_k": TOP_K,
                "golden_top3_processes": sorted(GOLDEN_TOP3_PROCESSES),
                "documents_indexed": result.versions_count,
                "total_input_tokens": result.total_input_tokens,
                "estimated_embedding_cost_usd": cost_usd,
                "after_index": first_measurement,
                "after_reindex_via_ai": second_measurement,
                "after_reindex_from_raw_vectors": {
                    **third_measurement,
                    "elapsed_seconds": raw_reindex_elapsed,
                    "raw_vectors_path": raw_vectors_path,
                    "subprocess_log": raw_reindex.stdout.strip(),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nResultado escrito em {OUTPUT_DIR / 'results.json'}")

    gate_passed = (
        first_measurement["gate_passed"]
        and second_measurement["gate_passed"]
        and third_measurement["gate_passed"]
    )
    print(
        f"\nGate Recall@3 >= 2/3 (index, reindex via ai e reindex sem AWS): "
        f"{'PASSOU' if gate_passed else 'FALHOU'}"
    )
    return 0 if gate_passed else 1


def _measure_recall(ai_client: AiClient, document_version_to_processo: dict, *, label: str) -> dict:
    response = ai_client.search(TEST_QUESTION, top_k=TOP_K)
    print(f"\n[{label}] model_version={response.model_version!r}, hits={len(response.hits)}")

    retrieved_processes: list[str] = []
    hits_summary = []
    for hit in response.hits:
        processo_raw = document_version_to_processo.get(hit.document_version)
        processo_canonical = canonical_process_for(processo_raw) if processo_raw else None
        hits_summary.append(
            {
                "document_version": hit.document_version,
                "family_id": hit.family_id,
                "score": hit.score,
                "processo_raw": processo_raw,
                "processo_canonical": processo_canonical,
                "excerpt_preview": hit.excerpt[:120],
            }
        )
        if processo_canonical and processo_canonical not in retrieved_processes:
            retrieved_processes.append(processo_canonical)
        print(
            f"  score={hit.score:.4f} doc={hit.document_version} "
            f"processo={processo_canonical} fam={hit.family_id}"
        )

    hits_in_golden = set(retrieved_processes) & GOLDEN_TOP3_PROCESSES
    recall_at_3 = len(hits_in_golden) / len(GOLDEN_TOP3_PROCESSES)
    gate_passed = recall_at_3 >= (2 / 3)

    print(f"  processos agregados no top-3: {retrieved_processes}")
    print(f"  Recall@3 = {len(hits_in_golden)}/3 = {recall_at_3:.3f} -- gate: {'PASSOU' if gate_passed else 'FALHOU'}")

    return {
        "model_version": response.model_version,
        "hits": hits_summary,
        "processes_retrieved_top3": retrieved_processes,
        "hits_in_golden": sorted(hits_in_golden),
        "recall_at_3": recall_at_3,
        "gate_passed": gate_passed,
    }


if __name__ == "__main__":
    raise SystemExit(main())
