"""Persistência de vetores brutos fora do índice (issue #73, I7).

O índice OpenSearch é derivado: "reexecutar sem AWS exige os embeddings
reais; o índice OpenSearch é derivado" (M1/I7-reproducibility). Esta
classe é o armazenamento fora do índice que torna isso possível -
``tools/reindex_from_raw_vectors.py`` lê daqui e reconstrói o índice sem
chamar o Bedrock de novo.

Formato em disco: JSONL append-only, nunca reescreve o arquivo inteiro a
cada chamada. Um corpus completo tem milhares de chunks; reescrever um
JSON de dezenas de MB a cada documento indexado (``_index_one_real`` é
chamado uma vez por documento) tornaria a indexação do corpus completo
O(n²) no número de chunks já gravados. Em vez disso:

- ``upsert_chunks`` só faz ``append`` de uma linha JSON por chunk.
- ``delete_document`` faz ``append`` de uma linha-tombstone
  ``{"_tombstone": document_version}``.
- ``load_all`` faz o replay do arquivo inteiro em ordem: o tombstone
  remove os chunks daquele ``document_version`` vistos até ali, e um
  ``chunk_id`` repetido depois de um tombstone (reindexação do mesmo
  documento) sobrevive normalmente - é exatamente a sequência que
  ``_index_one_real``/``reindex`` usam (delete_document seguido de
  upsert dos chunks novos).

Nunca lido pelo caminho de index/search em produção (essa é
responsabilidade exclusiva de ``VectorStore``/OpenSearch) - só existe
para o reindex offline sem AWS.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.vector_store import ChunkDoc


class RawVectorStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def upsert_chunks(self, chunks: list[ChunkDoc]) -> None:
        if not chunks:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    def delete_document(self, document_version: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"_tombstone": document_version}) + "\n")

    def delete_all(self) -> None:
        """Espelha ``VectorStore.delete_index`` (app/routes/reindex.py chama
        os dois juntos): apaga o arquivo inteiro, para que um reindex do
        zero enviando so um subconjunto do catalogo nao deixe vetores
        brutos de documentos fora desse subconjunto sobrevivendo."""
        self._path.unlink(missing_ok=True)

    def load_all(self) -> list[ChunkDoc]:
        return list(self._replay().values())

    def count(self) -> int:
        return len(self._replay())

    def _replay(self) -> dict[str, ChunkDoc]:
        chunks: dict[str, ChunkDoc] = {}
        if not self._path.exists():
            return chunks
        with self._path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                tombstone = record.get("_tombstone")
                if tombstone is not None:
                    for chunk_id in [
                        cid for cid, c in chunks.items() if c.document_version == tombstone
                    ]:
                        del chunks[chunk_id]
                    continue
                chunks[record["chunk_id"]] = ChunkDoc(**record)
        return chunks
