"""Reindexa o OpenSearch a partir dos vetores brutos persistidos, SEM
chamar o Bedrock (issue #73, AC "vetores brutos persistidos e reindex a
partir deles demonstrado sem chamar a AWS").

Este modulo deliberadamente nunca importa ``boto3`` nem
``app.embeddings.BedrockEmbedder`` - a unica forma de reconstruir o
indice aqui e ler os embeddings ja computados de
``app.raw_vectors.RawVectorStore`` (issue #73/I7: "vetores brutos usados
sao preservados fora do indice ... o indice OpenSearch e derivado") e
empurra-los direto para ``OpenSearchVectorStore``. Reexecutar isso com
credenciais AWS removidas do ambiente produz o mesmo indice.

``seed_and_measure.py`` chama ``reindex_from_raw_vectors`` diretamente
(mesmo processo) para demonstrar o AC ponta a ponta sobre o corpus do
caso 1. Tambem roda standalone:

    OPENSEARCH_URL=http://localhost:9200 \\
    RAW_VECTORS_PATH=hackathon/.pipeline-output/documents/_raw_vectors/<model_version>.jsonl \\
        python3.12 hackathon/tools/case1_recall/reindex_from_raw_vectors.py
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parents[2]
_AI_DIR = _REPO_ROOT / "hackathon" / "ai"

sys.path.insert(0, str(_AI_DIR))

# Nenhum import de app.embeddings/boto3 aqui de proposito - ver docstring.
from app.embeddings import DIMENSIONS, MODEL_VERSION  # noqa: E402
from app.raw_vectors import RawVectorStore  # noqa: E402
from app.vector_store import OpenSearchVectorStore, VectorStore, index_name_for_model_version  # noqa: E402

BATCH_SIZE = 500

DEFAULT_RAW_VECTORS_PATH = (
    _REPO_ROOT / "hackathon" / ".pipeline-output" / "documents" / "_raw_vectors" / f"{MODEL_VERSION}.jsonl"
)


@dataclass(frozen=True)
class ReindexFromRawSummary:
    chunks_indexed: int
    documents_indexed: int
    index_name: str
    elapsed_seconds: float


def reindex_from_raw_vectors(
    vector_store: VectorStore, raw_vectors_path: Path
) -> ReindexFromRawSummary:
    """Reconstroi ``vector_store`` do zero a partir de ``raw_vectors_path``,
    sem nenhuma chamada Bedrock/AWS (ver docstring do modulo)."""
    raw_store = RawVectorStore(raw_vectors_path)
    chunks = raw_store.load_all()
    if not chunks:
        raise ValueError(
            f"{raw_vectors_path} nao tem nenhum chunk (apos replay de tombstones) - nada para reindexar."
        )

    index_name = index_name_for_model_version(MODEL_VERSION)
    t0 = time.time()
    vector_store.delete_index(index_name)
    vector_store.ensure_index(index_name, DIMENSIONS)
    for start in range(0, len(chunks), BATCH_SIZE):
        vector_store.index_chunks(index_name, chunks[start : start + BATCH_SIZE])

    return ReindexFromRawSummary(
        chunks_indexed=len(chunks),
        documents_indexed=len({c.document_version for c in chunks}),
        index_name=index_name,
        elapsed_seconds=time.time() - t0,
    )


def main() -> int:
    opensearch_url = os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
    raw_vectors_path = Path(os.environ.get("RAW_VECTORS_PATH", str(DEFAULT_RAW_VECTORS_PATH)))

    if not raw_vectors_path.exists():
        print(f"ERRO: {raw_vectors_path} nao existe - nada para reindexar.", file=sys.stderr)
        return 1

    vector_store = OpenSearchVectorStore(opensearch_url)
    try:
        summary = reindex_from_raw_vectors(vector_store, raw_vectors_path)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print(
        f"Reindex a partir dos vetores brutos ({raw_vectors_path}) concluido em "
        f"{summary.elapsed_seconds:.1f}s: {summary.chunks_indexed} chunks, "
        f"{summary.documents_indexed} documentos, indice {summary.index_name!r} "
        "(sem nenhuma chamada Bedrock/AWS nesta execucao)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
