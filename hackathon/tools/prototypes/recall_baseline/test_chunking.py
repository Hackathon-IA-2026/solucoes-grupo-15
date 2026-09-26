"""Small deterministic unit tests for the structural chunker (issue #60).

Run with: python3.12 -m pytest hackathon/tools/prototypes/recall_baseline/test_chunking.py -q
(or plain `python3.12 test_chunking.py` from this directory -- no pytest
dependency required, see the __main__ block).
"""

from __future__ import annotations

from chunking import (
    MAX_TOKENS,
    TARGET_TOKENS,
    Block,
    chunk_document,
    count_tokens,
    is_heading,
    is_table_block,
    parse_page_marker,
    split_into_blocks,
)


def test_page_marker_parsing():
    assert parse_page_marker("<!-- page:1 -->") == 1
    assert parse_page_marker("<!-- page:42 -->") == 42
    assert parse_page_marker("some text") is None


def test_heading_detection():
    assert is_heading("I – DA IDENTIFICAÇÃO")
    assert is_heading("EXPOSIÇÃO DE MOTIVOS PARA O AUTO DE INFRAÇÃO")
    assert not is_heading("Este é um parágrafo comum, com texto em minúsculas.")
    assert not is_heading("")


def test_table_detection():
    table_lines = [
        "QLP                            PLA                     PAT1 (dias)",
        "20.247                         73%                     241",
    ]
    assert is_table_block(table_lines)
    prose_lines = ["Este é um parágrafo.", "Com duas linhas de texto corrido."]
    assert not is_table_block(prose_lines)


def test_split_into_blocks_tracks_pages_and_types():
    text = (
        "<!-- page:1 -->\n"
        "I – DA IDENTIFICAÇÃO\n"
        "\n"
        "Agente: Empresa Exemplo S.A.\n"
        "Processo: 48500.000000/2024-00\n"
        "\n"
        "<!-- page:2 -->\n"
        "Coluna A                 Coluna B                 Coluna C\n"
        "1                        2                        3\n"
    )
    blocks = split_into_blocks(text)
    assert [b.block_type for b in blocks] == ["heading", "paragraph", "table"]
    assert blocks[0].start_page == 1
    assert blocks[1].start_page == 1
    assert blocks[2].start_page == 2


def test_chunk_document_is_deterministic():
    text = (
        "<!-- page:1 -->\n"
        "I – DA IDENTIFICAÇÃO\n"
        "\n"
        + "Este é um parágrafo de teste com bastante texto repetido. " * 40
        + "\n"
    )
    chunks_a = chunk_document(text, "doc-1", "corpus-v1", "48500.000000-2024-00")
    chunks_b = chunk_document(text, "doc-1", "corpus-v1", "48500.000000-2024-00")
    assert [c.text for c in chunks_a] == [c.text for c in chunks_b]
    assert [c.chunk_id for c in chunks_a] == [c.chunk_id for c in chunks_b]


def test_chunk_document_respects_token_budget():
    text = (
        "<!-- page:1 -->\n"
        "I – DA IDENTIFICAÇÃO\n"
        "\n"
        + ("Este é um parágrafo de teste com bastante texto repetido para forçar múltiplos chunks. " * 200)
        + "\n"
    )
    chunks = chunk_document(text, "doc-1", "corpus-v1", "48500.000000-2024-00")
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= MAX_TOKENS


def test_chunk_metadata_present():
    text = "<!-- page:1 -->\nAlgum texto de teste.\n"
    chunks = chunk_document(text, "doc-x", "corpus-v1", "48500.000000-2024-00")
    assert len(chunks) == 1
    c = chunks[0]
    assert c.document_id == "doc-x"
    assert c.corpus_version == "corpus-v1"
    assert c.process_nup_raw == "48500.000000-2024-00"
    assert c.page_start == 1
    assert c.page_end == 1
    assert c.chunk_id == "doc-x#chunk-0000"


if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    for t in tests:
        t()
        print(f"OK  {t.__name__}")
    print(f"{len(tests)} tests passed")
