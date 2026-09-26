"""PROTOTYPE: step 2 of PDF -> Markdown (issue #59) — apply the removal criteria.

Step 1 (`extract_raw_text.py`) is purely mechanical: `pdftotext -layout` per
page, byte-for-byte. This script is the other half of the two-step pipeline:
it takes that raw per-page text and removes exactly what D14 says to remove
before the structural chunking stage —

  1. whole attachments (vistoria report, laudo técnico) when a PDF embeds one
     as a separate section (`--drop-pages`, page-range based, for future use:
     none of the 10 case-1-carolina-mmgd PDFs embed a full separate report —
     see the prototype README);
  2. "contrato social" sections (same mechanism as (1) when present);
  3. signatures and identification of who signed.

Everything that is *not* matched by a removal rule is copied through
unchanged, character for character, from the `pdftotext -layout` output —
this is what makes the result a verbatim copy rather than a paraphrase: the
script never rewrites a sentence, it only ever deletes lines/blocks that are
boilerplate (repeated page footers/corner stamps) or signature/certification
noise (digital signature stamps, "Documento assinado ..." blocks, SEI's
"Documento assinado eletronicamente por ..." paragraph).

The removal rules below were derived by manually reading the raw text of the
10 real PDFs in `hackathon/data/case-1-carolina-mmgd/` (SICNET-era documents
up to ~2023, SEI-era documents from 2024/2025 onward) — see this prototype's
README for the specific patterns found in each family of document and the
side-by-side excerpt.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

PAGE_MARKER_RE = re.compile(r"^<!-- pdftotext:page (\d+) -->$")

# --- line-level boilerplate: drop the whole line, keep everything else -----

LINE_DROP_PATTERNS = [
    # SEI running header/footer repeated on every page, e.g.
    # "Exposição de Motivos para Auto de Infração SFT/ANEEL. (0059363)   SEI 48500.901433/2024-53 / pg. 10"
    # "Voto Item 11 da 40° RPO em 02/12/2025 (0250898)   SEI 48500.901433/2024-53 / pg. 14"
    re.compile(r"^.*\(\d{6,8}\)\s+SEI\s+\d{4,5}\.\d{6}/\d{4}-\d{2}\s*/\s*pg\.\s*\d+\s*$"),
    # Older SICNET self-referencing page footer, e.g.
    # "Pág. 2 da Exposição de Motivos para Auto de Infração nº 0032/2018-SFE"
    re.compile(r"^\s*P[aá]g\.\s*\d+\s+d[ae]\s+Exposi[cç][aã]o de Motivos.*$", re.IGNORECASE),
    # SICNET single-line signature/certification footer.
    re.compile(r"^\s*Documento\s+assinado\s+digitalmente\.?\s*$", re.IGNORECASE),
    re.compile(
        r"^\s*Consulte a autenticidade deste documento em http://sicnet2\.aneel\.gov\.br"
        r"/sicnetweb/v\.aspx,?\s*informando o c[oó]digo de verifica[cç][aã]o\s+[0-9A-Fa-f]+\.?\s*$"
    ),
    # SICNET single-line "who signed" variant, e.g.
    # "Documento assinado digitalmente por Ricardo Lavorato Tili, Diretor, em 31/05/2023 às 11:41"
    re.compile(r"^\s*Documento assinado digitalmente por .+$", re.IGNORECASE),
]

# --- block-level boilerplate: a trigger line starts a run of lines to drop -

FIRST_LINE_PROTOCOL_STAMP_RE = re.compile(
    r"^\s*\d{4,5}\.\d{6}/\d{4}-\d{2}(-\d+)?\s*(\(ANEXO:\s*\d+\))?\s*$"
)

SIGNATURE_STAMP_RE = re.compile(
    r"^\s*\((Assinad[oa]\s+(digitalmente|digital)|Assinatura\s+digital)\)\s*$", re.IGNORECASE
)
SEI_SIGNED_BY_RE = re.compile(r"^\s*Documento assinado eletronicamente por\b", re.IGNORECASE)
SEI_AUTHENTICITY_RE = re.compile(
    r"^\s*A autenticidade deste documento pode ser conferida\b", re.IGNORECASE
)
SEI_REFERENCE_RE = re.compile(r"^\s*Refer[eê]ncia:\s*Processo n[ºo]\b", re.IGNORECASE)
GARBLED_STAMP_START_RE = re.compile(r"^\s*Documento\s*$")
GARBLED_STAMP_MARK_RE = re.compile(r"^\s*Documentoassinado\s*$", re.IGNORECASE)


def filter_lines(
    lines: list[str],
    drop_line_literals: frozenset[str] = frozenset(),
    drop_line_contains: tuple[str, ...] = (),
    strip_trailing_rubric_tokens: tuple[str, ...] = (),
) -> list[str]:
    """Drop boilerplate/signature lines and blocks; keep everything else verbatim."""
    out: list[str] = []
    i = 0
    n = len(lines)
    trailing_rubric_re = (
        re.compile(r"^(.*\S)\s{6,}(?:" + "|".join(re.escape(t) for t in strip_trailing_rubric_tokens) + r")\s*$")
        if strip_trailing_rubric_tokens
        else None
    )
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if any(pattern.match(stripped) for pattern in LINE_DROP_PATTERNS):
            i += 1
            continue

        if stripped in drop_line_literals:
            i += 1
            continue

        if any(token in stripped for token in drop_line_contains):
            i += 1
            continue

        if trailing_rubric_re is not None:
            match = trailing_rubric_re.match(line)
            if match:
                out.append(match.group(1))
                i += 1
                continue

        # Garbled overlapping stamp: "Documento" / "Documentoassinado" / ...
        # (pdftotext merges a rotated signature stamp with the running
        # footer on some SICNET cover pages). Consume through the
        # "Consulte a autenticidade..." line that closes the block.
        if GARBLED_STAMP_START_RE.match(stripped) and i + 1 < n and GARBLED_STAMP_MARK_RE.match(
            lines[i + 1].strip()
        ):
            j = i + 1
            while j < n and "consulte a autenticidade" not in lines[j].strip().lower():
                j += 1
            i = j + 1 if j < n else j
            continue

        # "(Assinado digitalmente)" / "(Assinatura digital)" stamp followed
        # by the signer's name and role — identification of who signed.
        if SIGNATURE_STAMP_RE.match(stripped):
            i += 1
            consumed = 0
            while i < n and lines[i].strip() and consumed < 3:
                i += 1
                consumed += 1
            continue

        # SEI's multi-line "Documento assinado eletronicamente por ..." plus
        # the authenticity paragraph and the "Referência: Processo nº ..."
        # line that follows it.
        if SEI_SIGNED_BY_RE.match(stripped):
            i = _skip_paragraph(lines, i)
            i = _skip_blank(lines, i)
            if i < n and SEI_AUTHENTICITY_RE.match(lines[i].strip()):
                i = _skip_paragraph(lines, i)
            i = _skip_blank(lines, i)
            if i < n and SEI_REFERENCE_RE.match(lines[i].strip()):
                i += 1
            continue

        out.append(line)
        i += 1
    return out


def _skip_paragraph(lines: list[str], i: int) -> int:
    n = len(lines)
    while i < n and lines[i].strip():
        i += 1
    return i


def _skip_blank(lines: list[str], i: int) -> int:
    n = len(lines)
    while i < n and not lines[i].strip():
        i += 1
    return i


def drop_first_line_protocol_stamp(lines: list[str]) -> list[str]:
    """Drop a bare process/protocol-number corner stamp, but only when it is
    the very first non-blank line of the page — this is how SICNET/SEI stamp
    the process number in the page's top margin on every page. A citation to
    the same-shaped number (e.g. a footnote's reference target) appears later
    in the page body, never as the page's first line, so this stays safe."""
    for idx, line in enumerate(lines):
        if line.strip() == "":
            continue
        if FIRST_LINE_PROTOCOL_STAMP_RE.match(line.strip()):
            return lines[:idx] + lines[idx + 1 :]
        break
    return lines


def collapse_blank_runs(lines: list[str]) -> list[str]:
    """Formatting only: collapse 3+ blank lines left behind by removals to 1."""
    out: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                out.append(line)
        else:
            blank_run = 0
            out.append(line)
    return out


def main() -> int:
    args = parse_args()
    raw_path = resolve_path(args.raw)
    out_path = resolve_path(args.out)
    spec = json.loads(Path(resolve_path(args.spec)).read_text(encoding="utf-8")) if args.spec else {}
    drop_pages = set(spec.get("drop_pages", []))
    drop_line_literals = frozenset(spec.get("drop_line_literals", []))
    drop_line_contains = tuple(spec.get("drop_line_contains", []))
    strip_trailing_rubric_tokens = tuple(spec.get("strip_trailing_rubric_tokens", []))

    text = raw_path.read_text(encoding="utf-8")
    pages = split_pages(text)

    kept_lines: list[str] = []
    dropped_pages: list[int] = []
    for page_no, page_lines in pages:
        if page_no in drop_pages:
            dropped_pages.append(page_no)
            continue
        kept_lines.append(f"<!-- page:{page_no} -->")
        page_lines = drop_first_line_protocol_stamp(page_lines)
        kept_lines.extend(
            filter_lines(
                page_lines, drop_line_literals, drop_line_contains, strip_trailing_rubric_tokens
            )
        )
        kept_lines.append("")

    kept_lines = collapse_blank_runs(kept_lines)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(kept_lines).rstrip() + "\n", encoding="utf-8")

    print(f"raw: {raw_path}")
    print(f"pages kept: {len(pages) - len(dropped_pages)} / {len(pages)}")
    if dropped_pages:
        print(f"pages dropped whole (anexo/contrato social): {dropped_pages}")
    print(f"markdown: {out_path}")
    return 0


def split_pages(text: str) -> list[tuple[int, list[str]]]:
    pages: list[tuple[int, list[str]]] = []
    current_no: int | None = None
    current_lines: list[str] = []
    for line in text.split("\n"):
        match = PAGE_MARKER_RE.match(line)
        if match:
            if current_no is not None:
                pages.append((current_no, current_lines))
            current_no = int(match.group(1))
            current_lines = []
        else:
            current_lines.append(line)
    if current_no is not None:
        pages.append((current_no, current_lines))
    return pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, help="path to the raw per-page text file")
    parser.add_argument("--out", required=True, help="path to write the filtered Markdown")
    parser.add_argument(
        "--spec",
        default=None,
        help="optional JSON file with {'drop_pages': [int, ...], 'drop_line_literals':"
        " [str, ...], 'drop_line_contains': [str, ...], 'notes': str}. drop_pages"
        " removes whole embedded attachments/contrato social (none needed for the"
        " current 10 PDFs); drop_line_literals removes a per-document repeated"
        " stamp/rubric line (e.g. initials the preparer stamped on every page)"
        " matched by exact stripped text; drop_line_contains removes any line"
        " containing one of the given substrings (for garbled multi-column ICP-"
        "Brasil signature stamps that pdftotext merges into the surrounding text)"
        " — always document why in 'notes'.",
    )
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
