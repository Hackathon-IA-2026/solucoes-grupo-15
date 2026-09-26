"""Run the Recall@3 baseline over the real case-1-carolina-mmgd corpus (#60).

Pipeline: structural chunking (chunking.py) -> Titan V2 embeddings
(embeddings.py) -> top-3 retrieval by dot product (vectors are normalized,
so dot product == cosine similarity) -> aggregation by processo (D16
normalization, process_map.py) -> Recall@3 against the golden Top 3.

Usage (from repo root, with AWS credentials sourced into the environment):

    source .env
    python3.12 hackathon/tools/prototypes/recall_baseline/run_recall_baseline.py

Writes `output/chunks.jsonl`, `output/query.json` and `output/results.json`
next to this script. Prints a human-readable summary to stdout.

This script makes real network calls to Bedrock (one `invoke_model` per
chunk, plus one for the query) -- no fixture, no simulated embeddings.
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chunking import MAX_TOKENS, OVERLAP_TOKENS, TARGET_TOKENS, TOKENIZER_NAME, chunk_document
from embeddings import DIMENSIONS, MODEL_ID, NORMALIZE, REGION, dot_product, embed_text, get_bedrock_runtime_client
from process_map import GOLDEN_TOP3_PROCESSES, canonical_process_for_folder

REPO_ROOT = Path(__file__).resolve().parents[4]
CORPUS_DIR = REPO_ROOT / "hackathon" / "data" / "case-1-carolina-mmgd"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

CORPUS_VERSION = "c6a8370"  # commit that produced the #59 Markdown extraction
TEST_QUESTION = "procure precedentes sobre fiscalização de atendimento a solicitações de conexão de MMGD"
TOP_K = 3


def discover_documents() -> list[tuple[str, str, Path]]:
    """Return (document_id, folder_name, path) for every .md in the corpus."""
    docs = []
    for path in sorted(CORPUS_DIR.glob("*/*.md")):
        document_id = str(path.relative_to(CORPUS_DIR)).rsplit(".md", 1)[0]
        folder_name = document_id.split("/")[0]
        docs.append((document_id, folder_name, path))
    return docs


def main() -> int:
    if "AWS_ACCESS_KEY_ID" not in os.environ and "AWS_PROFILE" not in os.environ:
        print(
            "AVISO: nenhuma credencial AWS visível no ambiente "
            "(AWS_ACCESS_KEY_ID/AWS_PROFILE). Rode `source .env` antes deste script.",
            file=sys.stderr,
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    documents = discover_documents()
    print(f"Documentos encontrados no corpus: {len(documents)}")

    all_chunks = []
    for document_id, folder_name, path in documents:
        text = path.read_text(encoding="utf-8")
        process_nup = canonical_process_for_folder(folder_name)
        chunks = chunk_document(
            text,
            document_id=document_id,
            corpus_version=CORPUS_VERSION,
            process_nup_raw=folder_name,
        )
        for c in chunks:
            c.__dict__["process_nup_canonical"] = process_nup
        all_chunks.extend(chunks)
        print(f"  {document_id:70s} -> {len(chunks):3d} chunks")

    print(f"Total de chunks no corpus: {len(all_chunks)}")

    client = get_bedrock_runtime_client()

    print(f"Invocando {MODEL_ID} ({REGION}) para a pergunta de teste...")
    t0 = time.time()
    query_result = embed_text(client, TEST_QUESTION)
    print(f"  query embedded em {time.time() - t0:.2f}s, tokens={query_result.input_token_count}")

    print(f"Invocando {MODEL_ID} para {len(all_chunks)} chunks (isso leva alguns minutos)...")
    t0 = time.time()
    chunk_records = []
    for i, c in enumerate(all_chunks):
        result = embed_text(client, c.text)
        chunk_records.append(
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "process_nup_raw": c.process_nup_raw,
                "process_nup_canonical": c.__dict__["process_nup_canonical"],
                "corpus_version": c.corpus_version,
                "section": c.section,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "chunk_token_count_tiktoken": c.token_count,
                "bedrock_input_token_count": result.input_token_count,
                "text": c.text,
                "embedding": result.vector,
            }
        )
        if (i + 1) % 50 == 0 or (i + 1) == len(all_chunks):
            print(f"  {i + 1}/{len(all_chunks)} chunks embedded ({time.time() - t0:.1f}s decorridos)")

    print(f"Embeddings de chunks concluídos em {time.time() - t0:.2f}s")

    # Rank all chunks by similarity to the query (dot product, vectors normalized).
    scored = [
        (dot_product(query_result.vector, rec["embedding"]), rec)
        for rec in chunk_records
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    top3 = scored[:TOP_K]

    retrieved_processes = []
    top3_summary = []
    for score, rec in top3:
        top3_summary.append(
            {
                "chunk_id": rec["chunk_id"],
                "document_id": rec["document_id"],
                "process_nup_canonical": rec["process_nup_canonical"],
                "section": rec["section"],
                "page_start": rec["page_start"],
                "page_end": rec["page_end"],
                "score": score,
            }
        )
        if rec["process_nup_canonical"] not in retrieved_processes:
            retrieved_processes.append(rec["process_nup_canonical"])

    retrieved_set = set(retrieved_processes)
    hits = retrieved_set & GOLDEN_TOP3_PROCESSES
    recall_at_3 = len(hits) / len(GOLDEN_TOP3_PROCESSES)
    gate_passed = recall_at_3 >= (2 / 3)

    config = {
        "model_id": MODEL_ID,
        "region": REGION,
        "dimensions": DIMENSIONS,
        "normalize": NORMALIZE,
        "similarity_metric": "dot_product (vetores normalizados == cosseno)",
        "tokenizer": TOKENIZER_NAME,
        "chunking": {
            "target_tokens": TARGET_TOKENS,
            "max_tokens": MAX_TOKENS,
            "overlap_tokens": OVERLAP_TOKENS,
        },
        "corpus_version": CORPUS_VERSION,
        "top_k": TOP_K,
    }

    results = {
        "config": config,
        "query": TEST_QUESTION,
        "total_documents": len(documents),
        "total_chunks": len(all_chunks),
        "top3": top3_summary,
        "processes_retrieved_top3": retrieved_processes,
        "golden_top3_processes": sorted(GOLDEN_TOP3_PROCESSES),
        "hits": sorted(hits),
        "recall_at_3": recall_at_3,
        "gate_threshold": 2 / 3,
        "gate_passed": gate_passed,
    }

    (OUTPUT_DIR / "query.json").write_text(
        json.dumps(
            {"query": TEST_QUESTION, "embedding": query_result.vector, "bedrock_input_token_count": query_result.input_token_count},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with (OUTPUT_DIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for rec in chunk_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    (OUTPUT_DIR / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 72)
    print(f"Pergunta: {TEST_QUESTION!r}")
    print(f"Top-{TOP_K} chunks recuperados:")
    for item in top3_summary:
        print(
            f"  score={item['score']:.4f}  processo={item['process_nup_canonical']}  "
            f"doc={item['document_id']}  secao={item['section']!r}  "
            f"paginas={item['page_start']}-{item['page_end']}"
        )
    print(f"Processos agregados no top-3: {retrieved_processes}")
    print(f"Gabarito (D16): {sorted(GOLDEN_TOP3_PROCESSES)}")
    print(f"Recall@3 = {len(hits)}/3 = {recall_at_3:.3f}")
    print(f"Gate (>= 2/3): {'PASSOU' if gate_passed else 'FALHOU'}")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
