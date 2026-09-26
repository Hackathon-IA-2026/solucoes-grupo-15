"""PROTOTYPE: deterministic PDF -> raw per-page text extraction.

This is step 1 of the two-step PDF -> Markdown pipeline (issue #59). It only
does the mechanical part: call `pdftotext -layout` page by page and emit one
plain-text file with explicit page markers. It never decides what is an
attachment, a "contrato social", or a signature block — that filtering
criteria is applied by hand (or by an LLM call) on top of this raw text, and
is documented in this prototype's README.

Rationale for `pdftotext -layout` instead of a Python PDF library: the real
corpus documents are official ANEEL text-layer PDFs (not scans), and
`-layout` preserves the reading order of columns/tables well enough for a
human/LLM filtering pass to work from, without extra dependencies beyond
poppler-utils (`/usr/bin/pdftotext`), which is already available on this
machine.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

PAGE_MARKER = "<!-- pdftotext:page {page} -->"


def main() -> int:
    args = parse_args()
    pdf_path = resolve_path(args.pdf)
    output_path = resolve_path(args.out)
    if not pdf_path.exists():
        print(f"pdf not found: {pdf_path}", file=sys.stderr)
        return 1

    page_count = count_pages(pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for page in range(1, page_count + 1):
            handle.write(PAGE_MARKER.format(page=page) + "\n")
            handle.write(extract_page(pdf_path, page))
            handle.write("\n")

    print(f"pdf: {pdf_path}")
    print(f"pages: {page_count}")
    print(f"raw text: {output_path}")
    return 0


def count_pages(pdf_path: Path) -> int:
    result = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"could not read page count for {pdf_path}")


def extract_page(pdf_path: Path, page: int) -> str:
    result = subprocess.run(
        [
            "pdftotext",
            "-layout",
            "-f",
            str(page),
            "-l",
            str(page),
            str(pdf_path),
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="path to the source PDF")
    parser.add_argument(
        "--out", required=True, help="path to write the raw per-page text file"
    )
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
