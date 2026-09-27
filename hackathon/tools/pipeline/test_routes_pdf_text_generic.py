"""Unit tests for routes/pdf_text_generic.py (issue #68).

Builds tiny real PDFs with `weasyprint` (already installed on this machine)
instead of depending on the real corpus, so this route's generic-rules-only
behavior — no per-document spec — is exercised without the 10 case-1 PDFs.

Run with: python3.12 -m pytest hackathon/tools/pipeline/test_routes_pdf_text_generic.py -q
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from routes.pdf_text_generic import EXTRACTOR_VERSION, PdfTextGenericRoute

WEASYPRINT_AVAILABLE = shutil.which("weasyprint") is not None

pytestmark = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE, reason="weasyprint CLI not installed"
)

_PAGE_CSS = (
    "@page { size: 2000px 1000px; margin: 20px; }"
    " body { font-family: monospace; white-space: pre; }"
)


def _make_pdf(tmp_path: Path, pages: list[str], name: str = "doc") -> Path:
    """One `<div>` per page, `page-break-after: always` between them, and
    `white-space: pre` so newlines inside a page come out as the exact same
    lines under `pdftotext -layout` — makes the fixture's expected raw text
    fully predictable."""
    body = "".join(
        f'<div style="page-break-after: always;">{page}</div>' if i < len(pages) - 1
        else f"<div>{page}</div>"
        for i, page in enumerate(pages)
    )
    html_path = tmp_path / f"{name}.html"
    html_doc = f"<html><head><style>{_PAGE_CSS}</style></head><body>{body}</body></html>"
    html_path.write_text(html_doc, encoding="utf-8")
    pdf_path = tmp_path / f"{name}.pdf"
    subprocess.run(
        ["weasyprint", str(html_path), str(pdf_path)], check=True, capture_output=True
    )
    return pdf_path


def test_extracts_real_content_and_removes_sicnet_signature_boilerplate(tmp_path: Path):
    pdf_path = _make_pdf(
        tmp_path,
        pages=[
            "CONTEUDO PRINCIPAL DA PAGINA UM\nSegunda linha de conteudo relevante.",
            "Documento assinado digitalmente.\n"
            "Consulte a autenticidade deste documento em"
            " http://sicnet2.aneel.gov.br/sicnetweb/v.aspx,"
            " informando o codigo de verificacao ABCDEF1234567890",
        ],
    )
    out_path = tmp_path / "out.md"
    result = PdfTextGenericRoute().extract(pdf_path, out_path)

    assert result.status == "extracted"
    assert result.extractor_version == EXTRACTOR_VERSION
    assert result.pages_total == 2
    assert result.pages_kept == 2
    assert result.markdown_path == out_path

    markdown = out_path.read_text(encoding="utf-8")
    assert "<!-- page:1 -->" in markdown
    assert "<!-- page:2 -->" in markdown
    assert "CONTEUDO PRINCIPAL DA PAGINA UM" in markdown
    assert "Segunda linha de conteudo relevante." in markdown
    assert "Documento assinado digitalmente" not in markdown
    assert "codigo de verificacao" not in markdown


def test_reports_pending_for_pdf_with_no_extractable_text(tmp_path: Path):
    # An (almost) blank page: no text layer worth extracting — this is the
    # "PDF sem texto" case the batch report must list as pending, per issue
    # #68's own acceptance criterion.
    pdf_path = _make_pdf(tmp_path, pages=["", ""])
    out_path = tmp_path / "out.md"
    result = PdfTextGenericRoute().extract(pdf_path, out_path)

    assert result.status == "pending"
    assert result.markdown_path is None
    assert not out_path.exists()
    assert "sem camada de texto" in (result.message or "")


def test_can_handle_only_pdf():
    route = PdfTextGenericRoute()
    assert route.can_handle("pdf") is True
    assert route.can_handle("html") is False
    assert route.can_handle(None) is False


def test_reports_error_when_source_is_not_a_valid_pdf(tmp_path: Path):
    bogus = tmp_path / "not-a-pdf.pdf"
    bogus.write_bytes(b"this is not a pdf file")
    result = PdfTextGenericRoute().extract(bogus, tmp_path / "out.md")
    assert result.status == "error"
    assert result.message
