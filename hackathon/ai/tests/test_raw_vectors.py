"""Contrato de RawVectorStore (issue #73, I7: "vetores brutos usados são
preservados fora do índice - reexecutar sem AWS exige os embeddings
reais; o índice OpenSearch é derivado").

Formato em disco e JSONL append-only (nunca reescreve o arquivo inteiro
a cada upsert - ver docstring de app/raw_vectors.py para o motivo:
milhares de chunks no corpus completo tornariam reescrita O(n) por
documento proibitivamente lenta). ``load_all`` faz o replay
(chunk mais recente por chunk_id vence; tombstone remove os chunks de
um document_version até aquele ponto do arquivo).
"""

from pathlib import Path

from app.raw_vectors import RawVectorStore
from app.vector_store import ChunkDoc


def _chunk(chunk_id: str, document_version: str, **overrides) -> ChunkDoc:
    fields = dict(
        chunk_id=chunk_id,
        document_version=document_version,
        family_id=f"fam-{document_version}",
        corpus_version="corpus-v1",
        model_version="model-v1",
        section=None,
        page_start=1,
        page_end=1,
        text="texto de teste",
        embedding=[0.1, 0.2, 0.3],
    )
    fields.update(overrides)
    return ChunkDoc(**fields)


def test_upsert_then_load_all_roundtrips_chunks(tmp_path: Path) -> None:
    store = RawVectorStore(tmp_path / "raw_vectors.jsonl")
    chunk = _chunk("docver-1#chunk-0000", "docver-1")

    store.upsert_chunks([chunk])

    [loaded] = store.load_all()
    assert loaded == chunk


def test_load_all_on_missing_file_is_empty(tmp_path: Path) -> None:
    store = RawVectorStore(tmp_path / "does-not-exist.jsonl")
    assert store.load_all() == []
    assert store.count() == 0


def test_upsert_same_chunk_id_overwrites_not_duplicates(tmp_path: Path) -> None:
    store = RawVectorStore(tmp_path / "raw_vectors.jsonl")
    chunk_v1 = _chunk("docver-1#chunk-0000", "docver-1", text="versão 1")
    chunk_v2 = _chunk("docver-1#chunk-0000", "docver-1", text="versão 2")

    store.upsert_chunks([chunk_v1])
    store.upsert_chunks([chunk_v2])

    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].text == "versão 2"


def test_delete_document_removes_only_its_chunks(tmp_path: Path) -> None:
    store = RawVectorStore(tmp_path / "raw_vectors.jsonl")
    store.upsert_chunks(
        [
            _chunk("docver-a#chunk-0000", "docver-a"),
            _chunk("docver-b#chunk-0000", "docver-b"),
        ]
    )

    store.delete_document("docver-a")

    remaining = store.load_all()
    assert [c.document_version for c in remaining] == ["docver-b"]


def test_delete_document_then_reupsert_survives(tmp_path: Path) -> None:
    """Mesma sequência que _index_one_real usa: delete_document seguido de
    upsert dos chunks novos - o append-only não pode deixar o tombstone
    matar os chunks reescritos depois dele."""
    store = RawVectorStore(tmp_path / "raw_vectors.jsonl")
    store.upsert_chunks([_chunk("docver-a#chunk-0000", "docver-a", text="antigo")])

    store.delete_document("docver-a")
    store.upsert_chunks([_chunk("docver-a#chunk-0000", "docver-a", text="novo")])

    [loaded] = store.load_all()
    assert loaded.text == "novo"


def test_delete_all_clears_everything(tmp_path: Path) -> None:
    store = RawVectorStore(tmp_path / "raw_vectors.jsonl")
    store.upsert_chunks([_chunk("docver-a#chunk-0000", "docver-a")])

    store.delete_all()

    assert store.load_all() == []


def test_delete_all_on_missing_file_is_a_noop(tmp_path: Path) -> None:
    store = RawVectorStore(tmp_path / "does-not-exist.jsonl")
    store.delete_all()  # nao deve levantar
    assert store.load_all() == []


def test_count_reflects_load_all_length(tmp_path: Path) -> None:
    store = RawVectorStore(tmp_path / "raw_vectors.jsonl")
    store.upsert_chunks(
        [_chunk("docver-a#chunk-0000", "docver-a"), _chunk("docver-a#chunk-0001", "docver-a")]
    )
    assert store.count() == 2
