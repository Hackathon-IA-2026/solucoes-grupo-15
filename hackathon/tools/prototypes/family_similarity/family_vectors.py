"""Builds one embedding vector per família from the chunks already embedded
by the Recall@3 baseline (issue #60).

This corpus has exactly one document (= one document_version) per família
(see `d4-data-dictionary.md`: família = identidade lógica de UMA peça
documental; nenhum dos 10 PDFs é uma versão retificada/republicada de
outro). So `document_id` in `recall_baseline/output/chunks.jsonl` already
*is* the family key for this corpus -- there is no separate family-merge
step to run here.

Engineering choice (documented, per issue #61's own instruction that this is
free): the per-family vector is the **mean of that family's chunk
embeddings, re-normalized to unit length**. Titan V2 embeddings here are
unit-length (`normalize: true`, #60); the plain mean of several unit vectors
is *not* unit-length in general, so it is re-normalized (divided by its own
L2 norm) after averaging -- this keeps dot product == cosine similarity for
the family-level vectors too, consistent with #60's similarity metric.

Why mean-of-chunks over other options (a lead-paragraph embedding, a
re-embedded summary, embedding of the whole document text in one call):
- No new Bedrock calls are needed -- the 342 chunk embeddings already exist
  in `recall_baseline/output/chunks.jsonl` (real, real credentials, #60).
  Re-embedding whole documents would also exceed Titan's per-call input
  limit for the two largest documents (57 and 71 pages).
- A structural mean over already-structurally-chunked text is a standard,
  defensible way to get a single document-level vector without inventing a
  new summarization step (which #60/D14 explicitly did not ask for and
  which would need its own calibration).
- The alternative of embedding only a lead excerpt (e.g. first page) would
  under-represent long multi-section documents (up to 81 chunks for one
  auto de infração) and bias the family vector towards boilerplate headers.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CHUNKS_PATH = (
    REPO_ROOT
    / "hackathon/tools/prototypes/recall_baseline/output/chunks.jsonl"
)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        raise ValueError("Vetor nulo não pode ser normalizado.")
    return [x / norm for x in vector]


def load_family_vectors(chunks_path: Path = CHUNKS_PATH) -> dict[str, dict]:
    """Returns {document_id: {"vector": [...], "n_chunks": int,
    "process_nup_canonical": str}} -- one entry per família (= per
    document_id, since this corpus has one version per família)."""

    sums: dict[str, list[float]] = {}
    counts: dict[str, int] = defaultdict(int)
    process_of: dict[str, str] = {}

    with chunks_path.open(encoding="utf-8") as fh:
        for line in fh:
            chunk = json.loads(line)
            doc_id = chunk["document_id"]
            vector = chunk["embedding"]
            if doc_id not in sums:
                sums[doc_id] = [0.0] * len(vector)
            acc = sums[doc_id]
            for i, value in enumerate(vector):
                acc[i] += value
            counts[doc_id] += 1
            process_of[doc_id] = chunk["process_nup_canonical"]

    families: dict[str, dict] = {}
    for doc_id, total in sums.items():
        n = counts[doc_id]
        mean = [x / n for x in total]
        families[doc_id] = {
            "vector": _l2_normalize(mean),
            "n_chunks": n,
            "process_nup_canonical": process_of[doc_id],
        }
    return families


if __name__ == "__main__":
    fams = load_family_vectors()
    print(f"{len(fams)} famílias carregadas de {CHUNKS_PATH}")
    for doc_id, info in sorted(fams.items()):
        norm = math.sqrt(sum(x * x for x in info["vector"]))
        print(
            f"  {doc_id!r}: {info['n_chunks']} chunks, "
            f"processo {info['process_nup_canonical']}, "
            f"||v||={norm:.6f}"
        )
