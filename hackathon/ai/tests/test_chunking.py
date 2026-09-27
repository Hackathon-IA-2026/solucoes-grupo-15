"""Testes do chunking estrutural real (issue #69).

Porta os testes deterministicos do protototipo do Recall@3 (issue #60,
`hackathon/tools/prototypes/recall_baseline/test_chunking.py`) para o
modulo `app.chunking`, adaptados a assinatura ``chunk_document(text,
document_version)`` (sem os campos ``process_nup_raw``/agregacao de
processo, que nao pertencem ao port VectorService - ver docstring de
app/chunking.py). Nenhuma chamada de rede - so tiktoken (determinístico,
sem AWS).
"""

from app.chunking import (
    MAX_TOKENS,
    chunk_document,
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
    chunks_a = chunk_document(text, "doc-1")
    chunks_b = chunk_document(text, "doc-1")
    assert [c.text for c in chunks_a] == [c.text for c in chunks_b]
    assert [c.chunk_id for c in chunks_a] == [c.chunk_id for c in chunks_b]


def test_chunk_document_respects_token_budget():
    text = (
        "<!-- page:1 -->\n"
        "I – DA IDENTIFICAÇÃO\n"
        "\n"
        + (
            "Este é um parágrafo de teste com bastante texto repetido para "
            "forçar múltiplos chunks. " * 200
        )
        + "\n"
    )
    chunks = chunk_document(text, "doc-1")
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= MAX_TOKENS


def test_chunk_metadata_present():
    text = "<!-- page:1 -->\nAlgum texto de teste.\n"
    chunks = chunk_document(text, "doc-x")
    assert len(chunks) == 1
    c = chunks[0]
    assert c.document_version == "doc-x"
    assert c.page_start == 1
    assert c.page_end == 1
    assert c.chunk_id == "doc-x#chunk-0000"


def test_oversized_table_block_is_split_with_header_repeated():
    """Cobre _split_table_block via chunk_document: uma tabela isolada
    (sem heading no mesmo buffer, para nao entrar na combinacao
    heading+primeira-linha-da-tabela que e um caso conhecido, ver
    README do protototipo/#60) maior que MAX_TOKENS e dividida em
    pecas <= MAX_TOKENS, cada uma com o cabecalho repetido."""
    header = "Coluna A          Coluna B          Coluna C"
    rows = "\n".join(f"linha{i}          valor{i}          fim{i}" for i in range(400))
    text = f"<!-- page:1 -->\n{header}\n{rows}\n"
    chunks = chunk_document(text, "doc-table")
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= MAX_TOKENS
        assert c.text.splitlines()[0] == header


def test_overlap_only_between_adjacent_paragraphs_not_across_heading():
    text = (
        "<!-- page:1 -->\n"
        "PRIMEIRA SEÇÃO\n\n"
        + ("Texto narrativo repetido para forçar múltiplos chunks. " * 60)
        + "\n\nSEGUNDA SEÇÃO\n\n"
        + ("Outro texto narrativo completamente diferente aqui. " * 60)
        + "\n"
    )
    chunks = chunk_document(text, "doc-overlap")
    assert len(chunks) >= 2
    # Nenhum chunk da segunda seção deve conter uma sobreposição herdada
    # da primeira seção (cruzar heading nunca gera overlap).
    for c in chunks:
        if c.section == "SEGUNDA SEÇÃO":
            assert "PRIMEIRA SEÇÃO" not in c.text
