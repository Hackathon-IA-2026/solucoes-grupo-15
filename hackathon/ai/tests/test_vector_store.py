"""Testes do indice vetorial em memoria (issue #69).

``InMemoryVectorStore`` e o dublê usado pelos testes de rota
(test_index_real.py, test_search_real.py, test_reindex.py) no lugar do
OpenSearch real - estes testes provam o contrato que qualquer adapter
(inclusive o real, ``OpenSearchVectorStore``) precisa cumprir: upsert
por chunk_id, delete por document_version, delete de indice inteiro e
busca por similaridade (produto escalar, vetores normalizados).
"""

from app.vector_store import ChunkDoc, InMemoryVectorStore, index_name_for_model_version


def _chunk(chunk_id: str, document_version: str, embedding: list[float], **overrides) -> ChunkDoc:
    defaults = dict(
        chunk_id=chunk_id,
        document_version=document_version,
        family_id=f"fam-{document_version}",
        corpus_version="corpus-v1",
        model_version="model-v1",
        section=None,
        page_start=1,
        page_end=1,
        text=f"texto do {chunk_id}",
        embedding=embedding,
    )
    defaults.update(overrides)
    return ChunkDoc(**defaults)


def test_index_name_for_model_version_is_slug_safe():
    raw = "amazon.titan-embed-text-v2:0-us-east-1-1024d-normalized"
    expected = "capiwatt-chunks-amazon.titan-embed-text-v2-0-us-east-1-1024d-normalized"
    assert index_name_for_model_version(raw) == expected


def test_search_ranks_by_dot_product_descending():
    store = InMemoryVectorStore()
    store.ensure_index("idx", 3)
    store.index_chunks(
        "idx",
        [
            _chunk("c1", "doc-1", [1.0, 0.0, 0.0]),
            _chunk("c2", "doc-2", [0.0, 1.0, 0.0]),
            _chunk("c3", "doc-3", [0.9, 0.1, 0.0]),
        ],
    )

    hits = store.search("idx", [1.0, 0.0, 0.0], top_k=2)

    assert [h.chunk_id for h in hits] == ["c1", "c3"]
    assert hits[0].score >= hits[1].score
    assert hits[0].family_id == "fam-doc-1"
    assert hits[0].excerpt == "texto do c1"


def test_index_chunks_upserts_by_chunk_id():
    store = InMemoryVectorStore()
    store.ensure_index("idx", 3)
    store.index_chunks("idx", [_chunk("c1", "doc-1", [1.0, 0.0, 0.0], text="versao antiga")])
    store.index_chunks("idx", [_chunk("c1", "doc-1", [1.0, 0.0, 0.0], text="versao nova")])

    hits = store.search("idx", [1.0, 0.0, 0.0], top_k=5)

    assert len(hits) == 1
    assert hits[0].excerpt == "versao nova"


def test_delete_document_removes_only_its_chunks():
    store = InMemoryVectorStore()
    store.ensure_index("idx", 3)
    store.index_chunks(
        "idx",
        [
            _chunk("c1", "doc-1", [1.0, 0.0, 0.0]),
            _chunk("c2", "doc-2", [0.0, 1.0, 0.0]),
        ],
    )

    store.delete_document("idx", "doc-1")

    hits = store.search("idx", [1.0, 1.0, 0.0], top_k=5)
    assert [h.document_version for h in hits] == ["doc-2"]
    assert store.count_chunks_for_document("idx", "doc-1") == 0
    assert store.count_chunks_for_document("idx", "doc-2") == 1


def test_delete_index_clears_everything():
    store = InMemoryVectorStore()
    store.ensure_index("idx", 3)
    store.index_chunks("idx", [_chunk("c1", "doc-1", [1.0, 0.0, 0.0])])

    store.delete_index("idx")

    assert store.search("idx", [1.0, 0.0, 0.0], top_k=5) == []


def test_search_on_unknown_index_returns_empty():
    store = InMemoryVectorStore()
    assert store.search("nunca-criado", [1.0, 0.0, 0.0], top_k=5) == []
