"""Constroi um vetor por familia a partir dos vetores brutos REAIS
persistidos pelo servico ``ai`` (issue #73, ``app/raw_vectors.py``) --
nao mais dos embeddings do protototipo (issue #60/#61,
``recall_baseline/output/chunks.jsonl``). Recalibracao da issue #74.

Fonte: ``hackathon/.pipeline-output/documents/_raw_vectors/amazon.titan-embed-text-v2-us-east-1-1024d-normalized.jsonl``,
gravado por ``RawVectorStore.upsert_chunks`` durante as execucoes reais de
``hackathon/tools/case1_recall/seed_and_measure.py`` (indexacao real via
``EMBEDDER=bedrock``, Postgres/OpenSearch locais - ver commit da #73). O
arquivo e formato JSONL append-only com tombstones (reindex do mesmo
documento); o replay correto (tombstone remove os chunks anteriores
daquele ``document_version``) e responsabilidade de ``RawVectorStore``, e
por isso ele e reaproveitado aqui em vez de reimplementado (evita
divergir da logica de producao que decide quais vetores estao "vivos").

Nao faz nenhuma chamada nova ao Bedrock/AWS -- so le o arquivo ja
commitado.

Escolha de engenharia mantida da issue #61 (nao reaberta aqui): o vetor
de familia e a **media dos embeddings de chunk, renormalizada para norma
unitaria**. Ver ``README.md`` deste pacote, secao "Estrategia de vetor de
agregacao (issue #74)", para a avaliacao da alternativa (vetor so do
trecho de "motivacao"/fundamentacao) e por que ela foi descartada para
este corpus.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_AI_DIR = _REPO_ROOT / "hackathon" / "ai"
if str(_AI_DIR) not in sys.path:
    # So "app.raw_vectors"/"app.vector_store" (modulo ai) sao importados
    # neste processo -- nunca "backend/app" no mesmo processo, que colide
    # em sys.modules["app"] (mesmo cuidado documentado em
    # seed_and_measure.py).
    sys.path.insert(0, str(_AI_DIR))

from app.raw_vectors import RawVectorStore  # noqa: E402
from app.vector_store import ChunkDoc  # noqa: E402

RAW_VECTORS_PATH = (
    _REPO_ROOT
    / "hackathon"
    / ".pipeline-output"
    / "documents"
    / "_raw_vectors"
    / "amazon.titan-embed-text-v2-us-east-1-1024d-normalized.jsonl"
)

# Heuristica usada so para a avaliacao (documentada no README) da secao
# "motivacao"/fundamentacao -- nunca para a agregacao usada na calibracao
# final (mean-of-all-chunks, ver acima).
_MOTIVACAO_SECTION_KEYWORDS = ("MOTIVA", "FUNDAMENTA", "MERITO", "MÉRITO")


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        raise ValueError("Vetor nulo não pode ser normalizado.")
    return [x / norm for x in vector]


def _mean_vector(chunks: list[ChunkDoc]) -> list[float]:
    dims = len(chunks[0].embedding)
    total = [0.0] * dims
    for chunk in chunks:
        for i, value in enumerate(chunk.embedding):
            total[i] += value
    n = len(chunks)
    return _l2_normalize([x / n for x in total])


def _is_motivacao_section(section: str | None) -> bool:
    if section is None:
        return False
    upper = section.upper()
    return any(keyword in upper for keyword in _MOTIVACAO_SECTION_KEYWORDS)


def load_family_vectors(raw_vectors_path: Path = RAW_VECTORS_PATH) -> dict[str, dict]:
    """Devolve ``{family_id: {"vector", "n_chunks", "n_motivacao_chunks",
    "motivacao_vector"}}`` -- um vetor de familia (media de TODOS os
    chunks, renormalizada) por ``family_id``, mais o vetor alternativo
    "so motivacao" quando a familia tem pelo menos um chunk classificado
    nessa secao (``None`` caso contrario -- ver README, a maioria das
    familias nao tem)."""

    store = RawVectorStore(raw_vectors_path)
    all_chunks = store.load_all()

    by_family: dict[str, list[ChunkDoc]] = {}
    for chunk in all_chunks:
        by_family.setdefault(chunk.family_id, []).append(chunk)

    families: dict[str, dict] = {}
    for family_id, chunks in by_family.items():
        motivacao_chunks = [c for c in chunks if _is_motivacao_section(c.section)]
        families[family_id] = {
            "vector": _mean_vector(chunks),
            "n_chunks": len(chunks),
            "n_motivacao_chunks": len(motivacao_chunks),
            "motivacao_vector": _mean_vector(motivacao_chunks) if motivacao_chunks else None,
        }
    return families


if __name__ == "__main__":
    fams = load_family_vectors()
    print(f"{len(fams)} familias carregadas de {RAW_VECTORS_PATH}")
    for family_id, info in sorted(fams.items()):
        norm = math.sqrt(sum(x * x for x in info["vector"]))
        print(
            f"  {family_id!r}: {info['n_chunks']} chunks "
            f"({info['n_motivacao_chunks']} de 'motivacao'), ||v||={norm:.6f}"
        )
