"""Structural chunking for the Recall@3 baseline (issue #60).

Implements the chunking decision fixed in D14 / M1
(`requirements/perspec-me/capiwatt-lens-hackathon/concerns/d14-data-operations-modeling.md`,
`m1-algorithm-model-selection.md`):

- target 600 tokens, maximum 800 tokens per chunk;
- 100-token overlap, only between adjacent *narrative* (paragraph) chunks —
  never across a heading/section boundary, and never involving a table;
- titles/sections/paragraphs/tables are used as the structural boundaries;
- whole tables are kept together when they fit; when a table must be split,
  the header line is repeated at the top of every continuation piece;
- chunks never cross a document (a document here = one `.md` file, one
  documental version) — there is only one version per document in this
  corpus, so this is automatic.

Tokenizer choice
-----------------
`tiktoken` (encoding `cl100k_base`) is used to count tokens. It is not the
tokenizer Titan itself uses internally, but the ticket only requires a
*deterministic, documented* choice, not the exact tokenizer Titan uses --
`cl100k_base` is installed, fast, dependency-light, and widely understood.
Every run of this chunker on the same input therefore produces byte-for-byte
identical chunks.

Page metadata
-------------
Unlike what issue #60 anticipated, the `.md` files produced by the #59
prototype (`pdf_to_markdown/filter_verbatim.py`) *do* carry an
`<!-- page:N -->` marker before each page's text, and no page was dropped
whole for any of the 10 documents (`pdf_to_markdown/README.md`, "pages kept:
N / N" for all ten) -- so these markers line up with the original PDF page
numbers. This chunker uses them to record `page_start`/`page_end` per chunk.
What is *not* attempted here (out of scope for #60, reserved for the future
small-to-big ticket) is reconstructing a *rendering* of the full pages for
context expansion -- only the page numbers are carried as metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import tiktoken

TARGET_TOKENS = 600
MAX_TOKENS = 800
OVERLAP_TOKENS = 100

TOKENIZER_NAME = "cl100k_base"
_ENCODING = tiktoken.get_encoding(TOKENIZER_NAME)

_PAGE_MARKER_RE = re.compile(r"^<!--\s*page:(\d+)\s*-->\s*$")

# A line counts as a section heading when it is short, made up almost only of
# uppercase letters (Portuguese accented uppercase included), and is not a
# columnar/table line. This matches the ANEEL document style seen across the
# corpus, e.g. "EXPOSIÇÃO DE MOTIVOS PARA O AUTO DE INFRAÇÃO",
# "I – DA IDENTIFICAÇÃO", "II – DOS FATOS".
_HEADING_MAX_LEN = 120
_HEADING_MIN_UPPER_RATIO = 0.8
_HEADING_MIN_ALPHA_CHARS = 3

# A line is considered "columnar" (part of a table rendered by
# `pdftotext -layout`) when it has an internal run of 2+ spaces between two
# non-space characters -- i.e. more than one field separated by padding.
_COLUMN_GAP_RE = re.compile(r"\S {2,}\S")
_TABLE_MIN_LINES = 2
_TABLE_MIN_COLUMNAR_RATIO = 0.6


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_ENCODING.encode(text))


def _decode_last_tokens(text: str, n: int) -> str:
    """Return the text corresponding to the last `n` tokens of `text`."""
    ids = _ENCODING.encode(text)
    if len(ids) <= n:
        return text
    return _ENCODING.decode(ids[-n:])


def parse_page_marker(line: str) -> Optional[int]:
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
    start_page: Optional[int]
    end_page: Optional[int]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass
class Chunk:
    document_id: str
    corpus_version: str
    process_nup_raw: str
    section: Optional[str]
    page_start: Optional[int]
    page_end: Optional[int]
    token_count: int
    text: str
    chunk_index: int = 0
    chunk_id: str = field(default="")

    def finalize_id(self) -> None:
        self.chunk_id = f"{self.document_id}#chunk-{self.chunk_index:04d}"


def split_into_blocks(markdown_text: str) -> list[Block]:
    """Split a `.md` document into heading/paragraph/table blocks.

    Blank lines are block separators. `<!-- page:N -->` markers are metadata
    only (never part of block text) and update the running page counter.
    A single-line block that looks like a heading is tagged `heading`; a
    multi-line block that looks columnar is tagged `table`; everything else
    is `paragraph`.
    """
    blocks: list[Block] = []
    current_lines: list[str] = []
    current_start_page: Optional[int] = None
    current_end_page: Optional[int] = None
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
    """Split an oversized table block into pieces, repeating the header line."""
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
    """Split an oversized paragraph block on sentence boundaries.

    A best-effort, documented approximation: splits after `.`, `;`, `:`,
    `!`, `?` followed by whitespace. Consecutive pieces overlap by up to
    `overlap_tokens` tokens of trailing text from the previous piece, since
    these are still adjacent narrative text within the same paragraph.
    """
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
        Block(lines=piece.split("\n"), block_type="paragraph", start_page=block.start_page, end_page=block.end_page)
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


def chunk_document(
    markdown_text: str,
    document_id: str,
    corpus_version: str,
    process_nup_raw: str,
) -> list[Chunk]:
    """Chunk one document's markdown text into structural chunks."""
    blocks = split_into_blocks(markdown_text)
    blocks = _normalize_oversized(blocks)

    chunks: list[Chunk] = []
    buffer: list[Block] = []
    buffer_tokens = 0
    current_section: Optional[str] = None
    chunk_section: Optional[str] = None

    def buffer_text() -> str:
        return "\n\n".join(b.text for b in buffer)

    def seed_overlap_if_any(last_flushed_type: Optional[str], next_block_type: Optional[str], flushed_text: str, edge_page: Optional[int]) -> None:
        """After a flush, materialize the overlap as a real block in the new
        (empty) buffer, so token-budget accounting for the next block stays
        correct. Only applies between adjacent narrative (paragraph) content
        -- never after/into a heading or a table."""
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

    def flush(next_block_type: Optional[str]) -> None:
        nonlocal buffer, buffer_tokens, chunk_section
        if not buffer:
            return
        pages = [b.start_page for b in buffer if b.start_page is not None] + [
            b.end_page for b in buffer if b.end_page is not None
        ]
        text = buffer_text()
        chunk = Chunk(
            document_id=document_id,
            corpus_version=corpus_version,
            process_nup_raw=process_nup_raw,
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
            # The flush above may have seeded a narrative overlap into the
            # new buffer; if that overlap plus this block would *still*
            # overflow the budget, drop the overlap for this one boundary
            # rather than emit a tiny overlap-only chunk and risk repeating
            # this indefinitely -- the block itself is already guaranteed
            # <= MAX_TOKENS by `_normalize_oversized`.
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
