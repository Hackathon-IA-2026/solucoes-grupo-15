"""Chunking estrutural real do modulo ai (issue #69).

Porta, quase verbatim, a logica validada pelo protototipo do Recall@3
(issue #60, gate PASSOU - `hackathon/tools/prototypes/recall_baseline/chunking.py`).
A decisao de parametros (600/800/100 tokens, tiktoken cl100k_base,
regras de heading/tabela/overlap) foi travada em D14/M1
(`requirements/perspec-me/capiwatt-lens-hackathon/concerns/d14-data-operations-modeling.md`,
`m1-algorithm-model-selection.md`) e nao e reaberta aqui - esta issue so
porta o codigo do protototipo para dentro do servico `ai`, para uso em
`/internal/v1/index` e `/internal/v1/reindex` (ver app/routes/index.py).

Diferenca em relacao ao protototipo: os campos ``process_nup_raw`` /
``process_nup_canonical`` (agregacao de processo, D16) nao pertencem ao
port ``VectorService`` - agregacao de processo e responsabilidade do
backend (dono do catalogo)/da avaliacao de Recall@3, nao do chunking em
si. Aqui ``Chunk`` carrega so o que o indice vetorial precisa:
``document_version``, ``chunk_id``, ``section``, paginas, contagem de
tokens e o texto.

Tokenizer, regras de heading/tabela/overlap e o tratamento dos
marcadores ``<!-- page:N -->`` sao identicos ao protototipo - ver o
README dele para a especificacao completa e o raciocinio por tras de
cada heuristica.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import tiktoken

TARGET_TOKENS = 600
MAX_TOKENS = 800
OVERLAP_TOKENS = 100

TOKENIZER_NAME = "cl100k_base"
_ENCODING = tiktoken.get_encoding(TOKENIZER_NAME)

_PAGE_MARKER_RE = re.compile(r"^<!--\s*page:(\d+)\s*-->\s*$")

# Heuristica de heading: linha curta, quase toda em maiusculas (inclui
# acentuacao em maiusculo), sem gap colunar de tabela. Ver
# hackathon/tools/prototypes/recall_baseline/README.md para exemplos
# reais do corpus (estilo ANEEL).
_HEADING_MAX_LEN = 120
_HEADING_MIN_UPPER_RATIO = 0.8
_HEADING_MIN_ALPHA_CHARS = 3

# Heuristica de tabela: bloco multi-linha onde a maioria das linhas tem
# um "gap" colunar (2+ espacos entre dois nao-espacos) - o layout que
# `pdftotext -layout` produz para tabelas.
_COLUMN_GAP_RE = re.compile(r"\S {2,}\S")
_TABLE_MIN_LINES = 2
_TABLE_MIN_COLUMNAR_RATIO = 0.6


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_ENCODING.encode(text))


def _decode_last_tokens(text: str, n: int) -> str:
    """Devolve o texto correspondente aos ultimos `n` tokens de `text`."""
    ids = _ENCODING.encode(text)
    if len(ids) <= n:
        return text
    return _ENCODING.decode(ids[-n:])


def parse_page_marker(line: str) -> int | None:
    m = _PAGE_MARKER_RE.match(line.strip())
    return int(m.group(1)) if m else None


def is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > _HEADING_MAX_LEN:
        return False
    if _COLUMN_GAP_RE.search(stripped):
        return False
    alpha_chars = [c for c in stripped if c.isalpha()]
    if len(alpha_chars) < _HEADING_MIN_ALPHA_CHARS:
        return False
    upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    return upper_ratio >= _HEADING_MIN_UPPER_RATIO


def is_table_block(lines: list[str]) -> bool:
    if len(lines) < _TABLE_MIN_LINES:
        return False
    columnar = sum(1 for line in lines if _COLUMN_GAP_RE.search(line.strip()))
    return (columnar / len(lines)) >= _TABLE_MIN_COLUMNAR_RATIO


@dataclass
class Block:
    lines: list[str]
    block_type: str  # "heading" | "paragraph" | "table"
    start_page: int | None
    end_page: int | None

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass
class Chunk:
    document_version: str
    section: str | None
    page_start: int | None
    page_end: int | None
    token_count: int
    text: str
    chunk_index: int = 0
    chunk_id: str = field(default="")

    def finalize_id(self) -> None:
        self.chunk_id = f"{self.document_version}#chunk-{self.chunk_index:04d}"


def split_into_blocks(markdown_text: str) -> list[Block]:
    """Divide um documento `.md` em blocos heading/paragraph/table.

    Linhas em branco sao separadores de bloco. Marcadores
    ``<!-- page:N -->`` sao so metadado (nunca fazem parte do texto do
    bloco) e atualizam o contador de pagina corrente.
    """
    blocks: list[Block] = []
    current_lines: list[str] = []
    current_start_page: int | None = None
    current_end_page: int | None = None
    page = None

    def flush() -> None:
        nonlocal current_lines, current_start_page, current_end_page
        if not current_lines:
            return
        if len(current_lines) == 1 and is_heading(current_lines[0]):
            block_type = "heading"
        elif is_table_block(current_lines):
            block_type = "table"
        else:
            block_type = "paragraph"
        blocks.append(
            Block(
                lines=list(current_lines),
                block_type=block_type,
                start_page=current_start_page,
                end_page=current_end_page,
            )
        )
        current_lines = []
        current_start_page = None
        current_end_page = None

    for raw_line in markdown_text.splitlines():
        marker_page = parse_page_marker(raw_line)
        if marker_page is not None:
            page = marker_page
            continue
        if raw_line.strip() == "":
            flush()
            continue
        if not current_lines:
            current_start_page = page
        current_end_page = page
        current_lines.append(raw_line)

    flush()
    return blocks


def _split_table_block(block: Block, max_tokens: int) -> list[Block]:
    """Divide um bloco de tabela grande demais, repetindo o cabecalho."""
    header = block.lines[0]
    rows = block.lines[1:]
    pieces: list[Block] = []
    current_rows: list[str] = [header]
    for row in rows:
        candidate = current_rows + [row]
        if count_tokens("\n".join(candidate)) > max_tokens and len(current_rows) > 1:
            pieces.append(
                Block(
                    lines=list(current_rows),
                    block_type="table",
                    start_page=block.start_page,
                    end_page=block.end_page,
                )
            )
            current_rows = [header, row]
        else:
            current_rows = candidate
    if current_rows and current_rows != [header]:
        pieces.append(
            Block(
                lines=list(current_rows),
                block_type="table",
                start_page=block.start_page,
                end_page=block.end_page,
            )
        )
    return pieces or [block]


def _split_paragraph_block(block: Block, max_tokens: int, overlap_tokens: int) -> list[Block]:
    """Divide um paragrafo grande demais em limites de frase, com overlap."""
    text = block.text
    sentences = re.split(r"(?<=[.;:!?])\s+", text)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if count_tokens(candidate) > max_tokens and current:
            pieces.append(current)
            overlap = _decode_last_tokens(current, overlap_tokens)
            current = f"{overlap} {sentence}".strip()
        else:
            current = candidate
    if current:
        pieces.append(current)
    return [
        Block(
            lines=piece.split("\n"),
            block_type="paragraph",
            start_page=block.start_page,
            end_page=block.end_page,
        )
        for piece in pieces
    ] or [block]


def _normalize_oversized(blocks: list[Block]) -> list[Block]:
    normalized: list[Block] = []
    for block in blocks:
        if count_tokens(block.text) <= MAX_TOKENS:
            normalized.append(block)
            continue
        if block.block_type == "table":
            normalized.extend(_split_table_block(block, MAX_TOKENS))
        else:
            normalized.extend(_split_paragraph_block(block, MAX_TOKENS, OVERLAP_TOKENS))
    return normalized


def chunk_document(markdown_text: str, document_version: str) -> list[Chunk]:
    """Divide o texto markdown de uma versao documental em chunks estruturais.

    Chunks nunca cruzam documento (um documento = um `document_version`
    aqui, chamada uma vez por documento em app/routes/index.py).
    """
    blocks = split_into_blocks(markdown_text)
    blocks = _normalize_oversized(blocks)

    chunks: list[Chunk] = []
    buffer: list[Block] = []
    buffer_tokens = 0
    current_section: str | None = None
    chunk_section: str | None = None

    def buffer_text() -> str:
        return "\n\n".join(b.text for b in buffer)

    def seed_overlap_if_any(
        last_flushed_type: str | None,
        next_block_type: str | None,
        flushed_text: str,
        edge_page: int | None,
    ) -> None:
        nonlocal buffer, buffer_tokens
        if last_flushed_type == "paragraph" and next_block_type == "paragraph":
            overlap_text = _decode_last_tokens(flushed_text, OVERLAP_TOKENS)
            overlap_block = Block(
                lines=overlap_text.split("\n"),
                block_type="paragraph",
                start_page=edge_page,
                end_page=edge_page,
            )
            buffer = [overlap_block]
            buffer_tokens = count_tokens(buffer_text())

    def flush(next_block_type: str | None) -> None:
        nonlocal buffer, buffer_tokens, chunk_section
        if not buffer:
            return
        pages = [b.start_page for b in buffer if b.start_page is not None] + [
            b.end_page for b in buffer if b.end_page is not None
        ]
        text = buffer_text()
        chunk = Chunk(
            document_version=document_version,
            section=chunk_section,
            page_start=min(pages) if pages else None,
            page_end=max(pages) if pages else None,
            token_count=count_tokens(text),
            text=text,
        )
        chunks.append(chunk)

        last_type = buffer[-1].block_type
        edge_page = buffer[-1].end_page
        buffer = []
        buffer_tokens = 0
        seed_overlap_if_any(last_type, next_block_type, text, edge_page)

    for idx, block in enumerate(blocks):
        next_type = blocks[idx + 1].block_type if idx + 1 < len(blocks) else None

        if block.block_type == "heading":
            current_section = block.text.strip()
            if buffer_tokens >= TARGET_TOKENS:
                flush(next_block_type="heading")
            if not buffer:
                chunk_section = current_section
            buffer.append(block)
            buffer_tokens = count_tokens(buffer_text())
            continue

        block_tokens = count_tokens(block.text)
        if buffer and (buffer_tokens + block_tokens > MAX_TOKENS):
            flush(next_block_type=block.block_type)
            if buffer and (buffer_tokens + block_tokens > MAX_TOKENS):
                buffer = []
                buffer_tokens = 0

        if not buffer:
            chunk_section = current_section

        buffer.append(block)
        buffer_tokens = count_tokens(buffer_text())

        if buffer_tokens >= TARGET_TOKENS:
            flush(next_block_type=next_type)

    flush(next_block_type=None)

    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i
        chunk.finalize_id()

    return chunks
