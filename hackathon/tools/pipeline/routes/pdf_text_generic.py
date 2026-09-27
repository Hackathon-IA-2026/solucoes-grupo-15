"""First extraction route (issue #68): native-text-layer PDF -> Markdown,
generic rules only — no per-document spec (that is issue #71's job).

Reuses issue #59's prototype verbatim, rather than re-implementing it:
`hackathon/tools/prototypes/pdf_to_markdown/extract_raw_text.py` (mechanical
`pdftotext -layout` per page) and `filter_verbatim.py` (the boilerplate/
signature removal rules that don't need a per-document spec — the page-
margin protocol stamp, the SICNET/SEI signature and certification
boilerplate). Loaded via `importlib` because the prototype is a pair of
standalone scripts (own `argparse` `main()`, not a package) — this route
calls their library functions directly and never shells out to them as
subprocesses.

## Page markers

Same format the prototype already writes: `<!-- page:N -->` before each
kept page's content (see `filter_verbatim.split_pages`/`main`). One PDF
page is one marker; a page dropped whole (`drop_pages`, unused by this
generic-only route — no per-document spec to name one) would simply not
appear.

## "PDF sem camada de texto" detection

`pdftotext -layout` succeeds even on a scanned PDF — it silently returns
almost nothing per page. This route treats that as "no route" rather than
"extracted almost-empty Markdown": if the raw extraction's average
non-whitespace character count per page is below `MIN_CHARS_PER_PAGE`, the
result is `status="pending"` with a message pointing at the OCR route
(issue #72), never `status="extracted"`.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

from . import ExtractionResult

EXTRACTOR_VERSION = "pdf_text_generic@1"
MIN_CHARS_PER_PAGE = 20

_PROTOTYPE_DIR = (
    Path(__file__).resolve().parents[3] / "tools" / "prototypes" / "pdf_to_markdown"
)


def _load_prototype_module(module_name: str) -> ModuleType:
    module_path = _PROTOTYPE_DIR / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(
        f"_pdf_to_markdown_prototype.{module_name}", module_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_extract_raw_text = _load_prototype_module("extract_raw_text")
_filter_verbatim = _load_prototype_module("filter_verbatim")

PAGE_MARKER_RE = re.compile(r"^<!-- pdftotext:page (\d+) -->$")


class PdfTextGenericRoute:
    name = "pdf_text_generic"
    extractor_version = EXTRACTOR_VERSION

    def can_handle(self, formato: str | None) -> bool:
        return formato == "pdf"

    def extract(self, source_path: Path, out_path: Path) -> ExtractionResult:
        try:
            page_count = _extract_raw_text.count_pages(source_path)
        except Exception as exc:  # pdfinfo failure: not a text-layer question, a real error
            return ExtractionResult(
                status="error",
                extractor_version=self.extractor_version,
                route=self.name,
                message=f"pdfinfo falhou: {exc}",
            )

        if page_count == 0:
            return ExtractionResult(
                status="error",
                extractor_version=self.extractor_version,
                route=self.name,
                message="pdfinfo reportou 0 páginas",
            )

        pages_text: list[str] = []
        for page in range(1, page_count + 1):
            try:
                pages_text.append(_extract_raw_text.extract_page(source_path, page))
            except Exception as exc:
                return ExtractionResult(
                    status="error",
                    extractor_version=self.extractor_version,
                    route=self.name,
                    message=f"pdftotext falhou na página {page}: {exc}",
                )

        total_chars = sum(len(re.sub(r"\s", "", text)) for text in pages_text)
        if total_chars / page_count < MIN_CHARS_PER_PAGE:
            return ExtractionResult(
                status="pending",
                extractor_version=self.extractor_version,
                route=self.name,
                pages_total=page_count,
                message=(
                    "sem camada de texto extraível (media de "
                    f"{total_chars / page_count:.1f} caracteres/página) — "
                    "candidato à rota de OCR (#72)"
                ),
            )

        raw_lines: list[str] = []
        for page_no, text in enumerate(pages_text, start=1):
            raw_lines.append(f"<!-- pdftotext:page {page_no} -->")
            raw_lines.extend(text.split("\n"))

        pages = _filter_verbatim.split_pages("\n".join(raw_lines))
        kept_lines: list[str] = []
        raw_line_count = 0
        for page_no, page_lines in pages:
            raw_line_count += len(page_lines)
            kept_lines.append(f"<!-- page:{page_no} -->")
            page_lines = _filter_verbatim.drop_first_line_protocol_stamp(page_lines)
            kept_lines.extend(_filter_verbatim.filter_lines(page_lines))
            kept_lines.append("")
        kept_lines = _filter_verbatim.collapse_blank_runs(kept_lines)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(kept_lines).rstrip() + "\n", encoding="utf-8")

        kept_line_count = sum(1 for line in kept_lines if line.strip())
        percent_removed = (
            100.0 * (1 - kept_line_count / raw_line_count) if raw_line_count else 0.0
        )

        return ExtractionResult(
            status="extracted",
            extractor_version=self.extractor_version,
            route=self.name,
            markdown_path=out_path,
            pages_total=page_count,
            pages_kept=len(pages),
            percent_removed=round(percent_removed, 1),
        )
