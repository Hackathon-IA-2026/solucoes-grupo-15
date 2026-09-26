"""Unit tests for routes/pdf_ocr.py (issue #72).

Same synthetic-PDF convention as test_routes_pdf_llm_spec.py (weasyprint
fixtures, no dependency on the real corpus) — the OCR/vision call itself is
always a fake `OcrFn` injected via the constructor, never a real Bedrock
call. The real Bedrock-vision pilot against the real page 24 of
recurso-48500.000639-2019-07.pdf (quality/cost comparison against
`tesseract`) lives in the issue #72 evidence pack, not here — see the
module docstring's "OCR mechanism chosen" section for the numbers.

A full-page scanned image is simulated with a real raster PNG (generated
via ImageMagick's `convert`, already installed on this machine) sized/
displayed so its physical area covers the whole synthetic page at >=150ppi
— the same structural signal `_page_has_full_page_scan_image` looks for on
the real corpus (see module docstring for the real-page measurements that
fixed the 0.6/150 thresholds).

Run with: python3.12 -m pytest hackathon/tools/pipeline/test_routes_pdf_ocr.py -q
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from routes.pdf_llm_spec import PdfLlmSpecRoute, SpecGenerationResult
from routes.pdf_ocr import (
    EXTRACTOR_VERSION,
    OcrPageResult,
    PdfOcrRoute,
    classify_pdf_pages,
)

WEASYPRINT_AVAILABLE = shutil.which("weasyprint") is not None
CONVERT_AVAILABLE = shutil.which("convert") is not None

pytestmark = pytest.mark.skipif(
    not (WEASYPRINT_AVAILABLE and CONVERT_AVAILABLE),
    reason="weasyprint/ImageMagick convert CLI not installed",
)

# Same page geometry as test_routes_pdf_llm_spec.py/test_routes_pdf_text_generic.py
# (proven to produce exactly one page per `page-break-after` div, including
# for wholly-empty pages) — content box after the 20px margin on each side
# is 1960x960 CSS px = 1470x720 pts = 20.417in x 10.0in.
_PAGE_CSS = (
    "@page { size: 2000px 1000px; margin: 20px; }"
    " body { font-family: monospace; white-space: pre; }"
)
_CONTENT_BOX_PX = (1960, 960)  # matches _PAGE_CSS's content box, in CSS px

EMPTY_SPEC = {
    "drop_pages": [],
    "drop_line_literals": [],
    "drop_line_contains": [],
    "strip_trailing_rubric_tokens": [],
    "notes": "nada específico encontrado além do filtro genérico",
}


def _make_full_page_scan_image(tmp_path: Path, name: str = "scan") -> Path:
    """A raster image whose *source* resolution, once displayed at the
    synthetic page's own content-box size (`_CONTENT_BOX_PX`, in CSS px ==
    pt * 4/3), clears both `MIN_IMAGE_PPI` (150) and `MIN_IMAGE_AREA_RATIO`
    (0.6, here ~1.0) — see module docstring for the real-page measurements
    this mirrors. 4000x2000 source over a 1470x720pt (20.417in x 10in)
    display area is ~196/200 ppi (x/y)."""
    png_path = tmp_path / f"{name}.png"
    subprocess.run(
        ["convert", "-size", "4000x2000", "xc:gray", str(png_path)],
        check=True,
        capture_output=True,
    )
    return png_path


def _full_page_image_html(scan_png: Path, extra_body: str = "") -> str:
    """A page whose body is a fixed-size wrapper (matching the page's own
    content box) containing an absolutely-positioned full-page `<img>` —
    absolute so it never contributes to flow height/pagination — plus
    optional normal-flow text on top of it (models a scanned page that also
    carries its own sparse/garbled native text layer, e.g. the real page 24
    of recurso-48500.000639-2019-07.pdf)."""
    width_px, height_px = _CONTENT_BOX_PX
    return (
        f'<div style="position:relative;width:{width_px}px;height:{height_px}px">'
        f'<img style="position:absolute;top:0;left:0;width:{width_px}px;height:{height_px}px"'
        f' src="file://{scan_png}">'
        f"{extra_body}"
        f"</div>"
    )


def _make_pdf_pages(tmp_path: Path, page_bodies: list[str], name: str = "doc") -> Path:
    """Like test_routes_pdf_llm_spec.py's `_make_pdf`, but takes raw HTML
    per page (so a page can be an `<img>` tag) instead of plain text."""
    body = "".join(
        f'<div style="page-break-after: always;">{page}</div>' if i < len(page_bodies) - 1
        else f"<div>{page}</div>"
        for i, page in enumerate(page_bodies)
    )
    html_path = tmp_path / f"{name}.html"
    html_doc = f"<html><head><style>{_PAGE_CSS}</style></head><body>{body}</body></html>"
    html_path.write_text(html_doc, encoding="utf-8")
    pdf_path = tmp_path / f"{name}.pdf"
    subprocess.run(
        ["weasyprint", str(html_path), str(pdf_path)], check=True, capture_output=True
    )
    return pdf_path


def _fake_generate_fn(spec: dict):
    def generate(raw_text: str) -> SpecGenerationResult:
        return SpecGenerationResult(
            spec=spec, model_id="fake-spec-model", region="us-east-1", input_tokens=1, output_tokens=1
        )

    return generate


def _fake_ocr_fn(text_by_call: list[str] | str):
    """Returns an OcrFn: either a fixed transcription, or one popped from a
    list per call (to give different pages different OCR text)."""
    calls: list[bytes] = []

    def ocr(image_bytes: bytes) -> OcrPageResult:
        calls.append(image_bytes)
        text = text_by_call.pop(0) if isinstance(text_by_call, list) else text_by_call
        return OcrPageResult(
            text=text, model_id="fake-ocr-model", region="us-east-1", input_tokens=200, output_tokens=50
        )

    ocr.calls = calls  # type: ignore[attr-defined]
    return ocr


def _route(tmp_path: Path, ocr_fn, spec: dict = EMPTY_SPEC) -> PdfOcrRoute:
    llm_spec_route = PdfLlmSpecRoute(
        generate_fn=_fake_generate_fn(spec), spec_cache_dir=tmp_path / "llm_specs"
    )
    return PdfOcrRoute(
        ocr_fn=ocr_fn, ocr_cache_dir=tmp_path / "ocr_pages", llm_spec_route=llm_spec_route
    )


def test_native_page_is_never_sent_to_ocr(tmp_path: Path):
    pdf_path = _make_pdf_pages(
        tmp_path,
        page_bodies=["CONTEUDO NATIVO PRINCIPAL DA PAGINA, BEM MAIOR QUE O LIMITE MINIMO DE CARACTERES"],
    )
    ocr_fn = _fake_ocr_fn("NUNCA DEVERIA APARECER")
    route = _route(tmp_path, ocr_fn)
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    assert result.extractor_version == EXTRACTOR_VERSION
    assert len(ocr_fn.calls) == 0
    markdown = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "CONTEUDO NATIVO PRINCIPAL" in markdown
    assert "NUNCA DEVERIA APARECER" not in markdown


def test_low_density_page_is_ocrd_and_merged_into_markdown(tmp_path: Path):
    pdf_path = _make_pdf_pages(tmp_path, page_bodies=[""])
    ocr_fn = _fake_ocr_fn("TEXTO RECUPERADO VIA OCR")
    route = _route(tmp_path, ocr_fn)
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"  # never "pending" — this route always resolves
    assert len(ocr_fn.calls) == 1
    markdown = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "TEXTO RECUPERADO VIA OCR" in markdown
    assert "via OCR/visão" in (result.message or "")
    assert "1/1 página" in (result.message or "")


def test_full_page_scan_image_triggers_ocr_even_with_readable_char_count(tmp_path: Path):
    # Models the real page 24 case: a full-page scanned image *plus* enough
    # garbled-but-not-empty native text to clear MIN_CHARS_PER_PAGE on its
    # own — only the structural image-coverage signal catches this page.
    scan_png = _make_full_page_scan_image(tmp_path)
    garbled_native_text = "<p>w ín ald o de Oliveira, w ín ald o de Oliveira, w ín ald o de Oliveira</p>"
    pdf_path = _make_pdf_pages(
        tmp_path, page_bodies=[_full_page_image_html(scan_png, extra_body=garbled_native_text)]
    )

    native_chars = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"], check=True, capture_output=True, text=True
    ).stdout
    assert len(native_chars.replace(" ", "").replace("\n", "")) >= 20  # sanity: not near-empty

    ocr_fn = _fake_ocr_fn("Ronaldo de Oliveira")
    route = _route(tmp_path, ocr_fn)
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    assert len(ocr_fn.calls) == 1  # the full-page-image signal fired despite readable char count
    markdown = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "Ronaldo de Oliveira" in markdown


def test_ocr_failure_falls_back_to_native_text_for_that_page_only(tmp_path: Path):
    pdf_path = _make_pdf_pages(tmp_path, page_bodies=[""])

    def failing_ocr(image_bytes: bytes) -> OcrPageResult:
        raise RuntimeError("bedrock indisponível (simulado)")

    route = _route(tmp_path, failing_ocr)
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    assert "OCR/visão falhou" in (result.message or "")


def test_ocr_cache_hit_avoids_a_second_ocr_call(tmp_path: Path):
    pdf_path = _make_pdf_pages(tmp_path, page_bodies=[""])
    ocr_fn = _fake_ocr_fn("TEXTO ESTAVEL")
    route = _route(tmp_path, ocr_fn)

    route.extract(pdf_path, tmp_path / "out1.md")
    assert len(ocr_fn.calls) == 1

    route.extract(pdf_path, tmp_path / "out2.md")
    assert len(ocr_fn.calls) == 1  # second extract() reuses the persisted OCR cache

    cache_files = list((tmp_path / "ocr_pages").glob("*.json"))
    assert len(cache_files) == 1


def test_whole_document_scanned_is_extracted_via_ocr_for_every_page(tmp_path: Path):
    # Distinct (if tiny) content per page, not two identical blank pages —
    # two byte-identical rendered pages would legitimately share one entry
    # in the content-addressed OCR cache (see module docstring, "Own
    # cache"), which would make this assertion about *page* count wrong
    # for a reason that has nothing to do with the behavior under test.
    pdf_path = _make_pdf_pages(tmp_path, page_bodies=["pg1", "pg2"])
    ocr_fn = _fake_ocr_fn(["PAGINA UM OCR", "PAGINA DOIS OCR"])
    route = _route(tmp_path, ocr_fn)
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    assert len(ocr_fn.calls) == 2
    assert "2/2 página" in (result.message or "")
    markdown = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "PAGINA UM OCR" in markdown
    assert "PAGINA DOIS OCR" in markdown


def test_llm_spec_filtering_still_applies_to_ocrd_text(tmp_path: Path):
    pdf_path = _make_pdf_pages(tmp_path, page_bodies=[""])
    ocr_fn = _fake_ocr_fn("CONTEUDO\nRUBRICA-FULANO")
    spec = {**EMPTY_SPEC, "drop_line_literals": ["RUBRICA-FULANO"]}
    route = _route(tmp_path, ocr_fn, spec=spec)
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    markdown = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "CONTEUDO" in markdown
    assert "RUBRICA-FULANO" not in markdown


def test_classify_pdf_pages_matches_route_detection(tmp_path: Path):
    scan_png = _make_full_page_scan_image(tmp_path)
    pdf_path = _make_pdf_pages(
        tmp_path,
        page_bodies=[
            "CONTEUDO NATIVO NORMAL, BEM MAIOR QUE O LIMITE MINIMO DE CARACTERES POR PAGINA",
            _full_page_image_html(scan_png),
        ],
    )
    page_count, degraded = classify_pdf_pages(pdf_path)
    assert page_count == 2
    assert degraded == [2]


def test_can_handle_only_pdf():
    route = PdfOcrRoute(ocr_fn=_fake_ocr_fn(""))
    assert route.can_handle("pdf") is True
    assert route.can_handle("html") is False
    assert route.can_handle(None) is False


def test_reports_error_when_source_is_not_a_valid_pdf(tmp_path: Path):
    bogus = tmp_path / "not-a-pdf.pdf"
    bogus.write_bytes(b"this is not a pdf file")
    route = _route(tmp_path, _fake_ocr_fn(""))
    result = route.extract(bogus, tmp_path / "out.md")
    assert result.status == "error"
    assert result.message
