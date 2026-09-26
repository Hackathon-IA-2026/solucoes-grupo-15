"""Second extraction route (issue #70): native SEI HTML -> Markdown,
deterministic, no LLM, no OCR. Handles the 612 HTML documents in the ANEEL
corpus (votos, notas técnicas, extratos de decisão da Diretoria, despachos,
memorandos, e-mails, ...) that #68's manifest/triage routes here via
`formato == "html"`.

## Why BeautifulSoup + lxml instead of hand-rolled regex or stdlib-only

Real SEI HTML mixes deeply nested `<div>`/`<span>` styling wrappers, genuine
content `<table>`s (some with `colspan`), and a boilerplate signature block
that itself contains nested `<table>`s (QRCode image + text). A regex over
raw HTML cannot reliably tell "a `<table>` that is part of the document's
merit" from "a `<table>` inside the signature wrapper" without effectively
re-implementing a DOM — fragile and unauditable. `html.parser`
(`HTMLParser`) is event-based, not a tree, so the same problem recurs one
level down. BeautifulSoup with the `lxml` parser gives a real, queryable DOM
and tolerates the malformed nesting some documents have (e.g. the "E-mail"
`tipo_documento`: a full second `<html>` document pasted inside the
outer one's `<body>` — lxml recovers a walkable tree from that; a
regex-based approach would not). Neither library ships with Python's
standard library, so this route is the first thing in
`hackathon/tools/pipeline/` to need a declared dependency — see
`hackathon/tools/pipeline/requirements.txt` (new file, install with
`python3.12 -m pip install -r hackathon/tools/pipeline/requirements.txt`).

## Encoding

Every one of the 612 real files declares `<meta http-equiv="Content-Type"
content="text/html; charset=iso-8859-1" />` (verified against the whole
corpus, not just a sample, while building this route — zero exceptions).
This route always decodes the source bytes as `iso-8859-1` — it never
sniffs or guesses, and never trusts a `<meta>` value inside the file, both
because the corpus is 100% consistent and because `iso-8859-1` can decode
any byte sequence (no `UnicodeDecodeError` is possible), so a wrong
assumption here cannot surface as a loud parse failure — it would surface as
silently wrong characters, which is worse. If a future file in the corpus
ever declares a different charset, this is the one place to make that
conditional. The Markdown is written as UTF-8, matching every other route in
this pipeline and the rest of the stack.

## Page markers

HTML has no notion of pages. Per the extraction-route contract
(`requirements/contracts/extraction-route.md` and `routes/__init__.py`'s
docstring), a route with no natural page boundary must document what it
puts in the marker: this route always emits exactly one `<!-- page:1 -->`
before the whole document's Markdown, and always reports
`pages_total = pages_kept = 1`. There is no `drop_pages`-style mechanism
here (nothing to attach it to) — a whole-document discard is instead a
`status="pending"` result (see "No extractable content" below).

## Verbatim content: what this route walks and how

The Markdown body is built by walking the parsed tree top-down, starting
from `<body>` (or the whole document if there is no `<body>` tag). `<p>`,
`<table>` and `<h1>`–`<h6>` are each their own Markdown block; a `<div>` is
a transparent container that this route recurses into looking for the same
tags, since SEI wraps genuine content in nested `<div>`s in some document
families (e.g. the "E-mail" `tipo_documento`'s `<div id="conteudo">`). Not
every real document puts its text inside a `<p>`, though — that same
`<div id="conteudo">` holds bare text and inline tags (`<b>Assunto</b>:
<br/>...`) with no wrapping `<p>` at all — so this route also collects any
direct child that is bare text or an inline tag (not `<script>`/`<style>`)
into a paragraph-like run, flushed as its own block whenever a real
block-level child is hit or the container ends (`_render_children`); a
`<br>` inside that run is a newline (a soft break, not a new block). Only
`<script>`, `<style>`, `<meta>`, `<title>`, `<link>` and `<hr>` never
contribute any text, at any level.

Within a kept block, inline text is gathered by walking every descendant
text node and inline tag (`<span>`, `<b>`, `<strong>`, `<i>`, `<em>`, `<u>`,
`<sup>`, `<sub>`, `<a>`, `<font>`, ...) and concatenating their text
verbatim; a `<br>` becomes a newline inside that block's text (a soft line
break, not a new Markdown block); an `<img>` contributes nothing (a
letterhead logo or a QRCode carries no extractable text — its `alt`
attribute, e.g. `"Timbre"`, is a UI label, not document content, so it is
not copied into the output either). An `<a>`'s `href` is never copied into
the Markdown — only its visible text — because the contract is verbatim
*visible* content, not a reformatting of the source into Markdown link
syntax the original document never had.

A `<table>` is rendered as a GFM Markdown table: its first `<tr>` becomes
the header row regardless of whether its cells are `<th>` or `<td>` (the
real corpus never uses `<th>` — confirmed across a 60-file random sample —
so this is a Markdown-syntax convenience, not a claim about which row is
semantically a header; the cell text itself is untouched). Two
formatting-only normalizations happen inside a cell, both because Markdown
table syntax has no other way to represent them, and both documented here
so they are auditable: (1) a newline inside a cell is replaced with a
single space (Markdown table cells cannot span lines); (2) a literal `|`
inside a cell is escaped as `\\|` (otherwise it would be parsed as a column
separator). Neither changes, drops, or reorders a single word. A `colspan`
on a cell is *not* re-simulated as merged Markdown columns (GFM has no
notion of colspan) — the cell's text is kept exactly once, in its own
column, and this route pads the row with empty trailing cells so every row
in the table has the same column count as the header (a rendering
convenience, never a duplication of text). A `<table>` nested inside another
table's cell (rare — seen in 1 of a 60-file random sample) is flattened to
that cell's plain text, since Markdown does not support a table inside a
table cell; this loses only the nested grid's visual alignment, never any
word of its text.

## Signature/CRC block removal (auditable, structural)

SEI's own HTML export marks the entire final e-signature block — the
"Documento assinado eletronicamente por <b>NOME</b>, <b>CARGO</b>, em
DATA..." paragraph, its accompanying QRCode `<img>`, and the "A
autenticidade deste documento pode ser conferida..., código verificador
<b>N</b> e o código CRC <b>X</b>" paragraph that follows it — inside one
`<div unselectable="on" style="...user-select:none...">`. This was verified
against the entire real corpus while building this route (not a sample):
every one of the 612 files has *exactly* zero or one such `<div>` — the 14
documents with no signature at all (`tipo_documento` "E-mail": SEI never
signs those) simply have zero such `<div>`s. This route removes the whole
`<div unselectable="on">` when present — never a text/regex match on the
signature paragraph's wording, so a future rewording of the boilerplate by
SEI would fail loudly (nothing removed, `assinado eletronicamente` still in
the output, caught by this route's own tests) rather than silently keep
matching or start over-matching real content. That last property is not
theoretical: one real file in the corpus
(`processos aneel/.../48500.023369_2026-23/012_SEI_0458706_Oficio_1390.html`)
has the phrase "assinado eletronicamente" *twice* — once inside the
`<div unselectable="on">` (the real SEI stamp, removed) and once inside a
party's own quoted statement ("a MQA reconhece ter assinado eletronicamente
com a Copel Comercialização..." — substantive case content). This route
keeps the second occurrence verbatim, exactly because removal is scoped to
the structural `<div>`, never to the phrase itself. A whole-document,
end-to-end scan for residual `assinado eletronicamente`/`código
verificador`/`código CRC` across every one of the 420 real, non-discarded
HTML documents the corpus has (done while building this route — see the
issue #70 evidence pack) found exactly this one expected non-boilerplate
occurrence and no others.

## Reference/footer table removal (auditable, structural + textual)

Immediately after the signature block, every signed document also carries
a second, separate boilerplate element: a one-row `<table>` whose entire
text is exactly "Referência: Processo nº <processo> SEI nº <numero>" —
administrative metadata (the same process/SEI numbers already recorded in
the manifest for this document), not content of merit. This route removes
a `<table>` only when its whole stripped text matches
`_REFERENCE_FOOTER_RE` end-to-end (not "contains", not "starts with") — a
table that happens to mention "Referência" as part of real content (never
observed in the corpus, but not ruled out) would not match and would be
kept. Investigated and deliberately *not* removed: content the SEI editor
places textually *after* this footer table in some document families (seen
in `Despacho`s) — a second, more compact rendition of the same despacho
(its "ementa"/publication form) with its own distinct wording. It is not a
repeat of the boilerplate above, so it stays, verbatim, in document order.

`<hr>` elements are always dropped everywhere in the document (not just
around the signature block) — they never carry text, so dropping one is
never a content removal, only ever a no-op on the Markdown body.

## Known limitation: CSS-counter-generated list markers (not solved here)

Some SEI documents (e.g. `48500.021143/2025-15`'s Nota Técnica 150 — a real
file in the corpus) apply a CSS class (seen in the wild: `Item_Alinea_Letra`,
`Paragrafo_Numerado_Nivel1`) whose numbering/lettering marker ("a)", "1.",
"i)"...) is generated purely by a CSS `content: counter(...)` rule in the
document's own `<style>` block, never present as a text node. A static DOM
walker — this route, or any other purely-structural HTML->text approach —
cannot see CSS-generated content, so that marker is simply absent from the
Markdown output while the item's actual sentence is preserved unchanged.
This is a property of the source document's presentation layer that
pre-exists this route; it is not a removal this route performs (there is no
text to remove — the marker was never a DOM node), and reconstructing it
would require simulating CSS counters or rendering the page in a real
browser, neither of which fits "deterministic, no LLM, no OCR". Documented
here for auditability; out of scope for #70.

## No extractable content

If, after removing the boilerplate above, the document has no `<p>`,
`<table>` or heading left with any text, this route returns
`status="pending"` (never a silent `status="extracted"` with empty content —
the same rule `routes/pdf_text_generic.py` follows for a PDF with no text
layer). A read/parse failure (e.g. the file cannot be decoded, which should
never happen with `iso-8859-1`, or `lxml` raises) is `status="error"`.
"""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Tag

from . import ExtractionResult

EXTRACTOR_VERSION = "html_sei@1"

SOURCE_ENCODING = "iso-8859-1"

_BLOCK_TAGS = ("p", "div", "table", "h1", "h2", "h3", "h4", "h5", "h6")
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

_REFERENCE_FOOTER_RE = re.compile(
    r"^Refer[êe]ncia:\s*Processo\s*n[ºo°]\.?\s*[\d./-]+\s+SEI\s*n[ºo°]\.?\s*\d+$",
    re.IGNORECASE,
)


class HtmlSeiRoute:
    name = "html_sei"
    extractor_version = EXTRACTOR_VERSION

    def can_handle(self, formato: str | None) -> bool:
        return formato == "html"

    def extract(self, source_path: Path, out_path: Path) -> ExtractionResult:
        try:
            raw_bytes = source_path.read_bytes()
            html_text = raw_bytes.decode(SOURCE_ENCODING)
            soup = BeautifulSoup(html_text, "lxml")
        except Exception as exc:  # unexpected: iso-8859-1 decode never raises
            return ExtractionResult(
                status="error",
                extractor_version=self.extractor_version,
                route=self.name,
                message=f"falha ao ler/parsear o HTML: {exc}",
            )

        root = soup.body or soup
        _strip_never_content_tags(root)  # script/style/meta/title/link/img/hr
        raw_chars = _non_whitespace_len(root.get_text())

        _strip_signature_and_reference_footer(root)

        blocks = _render_children(root)

        if not blocks:
            return ExtractionResult(
                status="pending",
                extractor_version=self.extractor_version,
                route=self.name,
                pages_total=0,
                message="sem conteúdo extraível após remover o boilerplate de assinatura/CRC",
            )

        body_markdown = "\n\n".join(blocks)
        markdown = f"<!-- page:1 -->\n\n{body_markdown}\n"

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")

        kept_chars = _non_whitespace_len(body_markdown)
        percent_removed = 100.0 * (1 - kept_chars / raw_chars) if raw_chars else 0.0

        return ExtractionResult(
            status="extracted",
            extractor_version=self.extractor_version,
            route=self.name,
            markdown_path=out_path,
            pages_total=1,
            pages_kept=1,
            percent_removed=round(max(percent_removed, 0.0), 1),
        )


def _non_whitespace_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _is_signature_block(tag: Tag) -> bool:
    return tag.name == "div" and (tag.get("unselectable") or "").strip().lower() == "on"


def _is_reference_footer_table(tag: Tag) -> bool:
    if tag.name != "table":
        return False
    normalized = " ".join(tag.get_text(" ", strip=True).split())
    return bool(_REFERENCE_FOOTER_RE.match(normalized))


def _strip_never_content_tags(root: Tag) -> None:
    """Remove tags that never carry document text, regardless of position —
    run *before* `raw_chars` is measured in `extract()`, so that count
    reflects genuine document content, never CSS/JS text or decorative
    images/rules that were never going to be extracted either way."""
    for tag_name in ("script", "style", "meta", "title", "link", "hr", "img"):
        for tag in root.find_all(tag_name):
            tag.decompose()


def _strip_signature_and_reference_footer(root: Tag) -> None:
    """Remove exactly the two boilerplate elements documented in this
    module's docstring — the SEI signature/CRC `<div>` and the
    process/SEI-number reference footer `<table>`. Mutates `root` in place
    (the caller only walks it after this call). Run *after* `raw_chars` is
    measured, so `percent_removed` reflects what this rule actually removed."""
    for div in root.find_all("div"):
        if _is_signature_block(div):
            div.decompose()

    for table in root.find_all("table"):
        if _is_reference_footer_table(table):
            table.decompose()


_INLINE_SKIP_TAGS = {"script", "style"}
# A `<table>` nested inside a cell (rare — see module docstring) is
# flattened to plain text by this same walker; inserting a space at each of
# these tag boundaries keeps adjacent cells'/rows' text from running
# together word-to-word (e.g. "Nome" + "Idade" staying "Nome Idade", not
# "NomeIdade"). Harmless elsewhere: table/tr/td/th never nest inside a `<p>`
# in real HTML (a `<table>` is block-level and is always handled as its own
# top-level block by `_render_block`, never fed into a paragraph's
# `_inline_text`), so this never touches ordinary paragraph text.
_CELL_BOUNDARY_TAGS = {"table", "tr", "td", "th"}


def _inline_text(tag: Tag) -> str:
    """Gather verbatim visible text from `tag` and its descendants, turning
    a `<br>` into a newline (a soft break within the same block) and an
    `<img>` into nothing (see module docstring). Never copies an `<a>`'s
    `href` — only its visible text."""
    parts: list[str] = []
    for node in tag.descendants:
        if isinstance(node, Tag):
            if node.name == "br":
                parts.append("\n")
            elif node.name in _CELL_BOUNDARY_TAGS:
                parts.append(" ")
            continue
        # NavigableString: skip text nodes that live inside a tag we never
        # treat as content (defensive — script/style are already stripped
        # by _strip_never_content_tags before this runs).
        if node.parent is not None and node.parent.name in _INLINE_SKIP_TAGS:
            continue
        parts.append(str(node))
    return "".join(parts)


def _render_block(tag: Tag) -> list[str]:
    if tag.name == "p":
        text = _inline_text(tag).strip()
        return [text] if text else []

    if tag.name in _HEADING_TAGS:
        text = _inline_text(tag).strip()
        if not text:
            return []
        level = int(tag.name[1])
        return [f"{'#' * level} {text}"]

    if tag.name == "table":
        rendered = _render_table(tag)
        return [rendered] if rendered else []

    if tag.name == "div":
        if _is_signature_block(tag):
            return []  # already decomposed by _strip_signature_and_reference_footer; defensive
        return _render_children(tag)

    return []


def _render_children(container: Tag) -> list[str]:
    """Walk `container`'s direct children in document order, treating
    `<p>`/`<div>`/`<table>`/`<h1>`-`<h6>` as their own Markdown blocks
    (recursing into a `<div>`) and accumulating any other direct child —
    bare text, `<br>`, or an inline tag like `<b>`/`<a>` sitting straight
    inside `container` with no wrapping `<p>` — into a paragraph-like text
    run, flushed as its own block whenever a real block-level child is hit
    or the container ends. This matters for real SEI documents: the
    "E-mail" `tipo_documento`'s `<div id="conteudo">` has exactly this
    shape (`<b>Assunto</b>: <br/>&nbsp;&nbsp;texto<br/>` with no `<p>` at
    all) — without this fallback, that content would be silently dropped
    (see this route's own tests for the regression check)."""
    blocks: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        text = "".join(buffer).strip()
        if text:
            blocks.append(text)
        buffer.clear()

    for child in container.children:
        if isinstance(child, Tag):
            if child.name in _BLOCK_TAGS:
                flush()
                blocks.extend(_render_block(child))
            elif child.name == "br":
                buffer.append("\n")
            elif child.name in _INLINE_SKIP_TAGS:
                continue
            else:
                buffer.append(_inline_text(child))
        else:
            buffer.append(str(child))

    flush()
    return blocks


def _direct_rows(table: Tag) -> list[Tag]:
    """`<tr>` children of `table`, whether they sit directly under it or
    under a `<thead>`/`<tbody>`/`<tfoot>` wrapper — but never a `<tr>` that
    belongs to a table nested inside one of this table's cells."""
    rows: list[Tag] = []
    for child in table.find_all(["tr", "thead", "tbody", "tfoot"], recursive=False):
        if child.name == "tr":
            rows.append(child)
        else:
            rows.extend(child.find_all("tr", recursive=False))
    return rows


def _render_table(table: Tag) -> str | None:
    rows: list[list[str]] = []
    for tr in _direct_rows(table):
        cells: list[str] = []
        for cell in tr.find_all(["td", "th"], recursive=False):
            cell_text = _inline_text(cell)
            cell_text = " ".join(cell_text.split())  # newline-in-cell -> space
            cell_text = cell_text.replace("|", "\\|")
            colspan = _positive_int(cell.get("colspan"))
            cells.append(cell_text)
            cells.extend([""] * (colspan - 1))
        if cells:
            rows.append(cells)

    if not rows:
        return None

    width = max(len(row) for row in rows)
    for row in rows:
        row.extend([""] * (width - len(row)))

    header, *body_rows = rows
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in body_rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _positive_int(value: str | None) -> int:
    try:
        parsed = int(value) if value else 1
    except ValueError:
        return 1
    return parsed if parsed > 0 else 1
