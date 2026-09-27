"""Unit tests for routes/pdf_llm_spec.py (issue #71).

Same synthetic-PDF convention as test_routes_pdf_text_generic.py (weasyprint
fixtures, no dependency on the real corpus) — but the Bedrock call itself is
always a fake `GenerateFn` injected via the constructor, never a real
network/API call, per issue #71's own instruction to mock Bedrock in
automated tests. The real-Bedrock validation (10 case-1 PDFs, category 04
pilot, token/cost logging) lives in the issue #71 evidence pack, not here.

Run with: python3.12 -m pytest hackathon/tools/pipeline/test_routes_pdf_llm_spec.py -q
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from routes.pdf_llm_spec import (
    EXTRACTOR_VERSION,
    PROMPT_VERSION,
    PdfLlmSpecRoute,
    SpecGenerationResult,
    _spec_cache_key,
    estimate_cost_usd,
)

WEASYPRINT_AVAILABLE = shutil.which("weasyprint") is not None

pytestmark = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE, reason="weasyprint CLI not installed"
)

_PAGE_CSS = (
    "@page { size: 2000px 1000px; margin: 20px; }"
    " body { font-family: monospace; white-space: pre; }"
)

EMPTY_SPEC = {
    "drop_pages": [],
    "drop_line_literals": [],
    "drop_line_contains": [],
    "strip_trailing_rubric_tokens": [],
    "notes": "nada específico encontrado além do filtro genérico",
}


def _make_pdf(tmp_path: Path, pages: list[str], name: str = "doc") -> Path:
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


def _fake_generate_fn(spec: dict, calls: list[str] | None = None):
    def generate(raw_text: str) -> SpecGenerationResult:
        if calls is not None:
            calls.append(raw_text)
        return SpecGenerationResult(
            spec=spec,
            model_id="fake-model",
            region="us-east-1",
            input_tokens=123,
            output_tokens=45,
        )

    return generate


def test_applies_llm_generated_spec_to_drop_document_specific_rubric(tmp_path: Path):
    pdf_path = _make_pdf(
        tmp_path,
        pages=[
            "CONTEUDO PRINCIPAL DA PAGINA UM\nRUBRICA-FULANO",
            "CONTEUDO PRINCIPAL DA PAGINA DOIS\nRUBRICA-FULANO",
        ],
    )
    spec = {**EMPTY_SPEC, "drop_line_literals": ["RUBRICA-FULANO"]}
    route = PdfLlmSpecRoute(generate_fn=_fake_generate_fn(spec), spec_cache_dir=tmp_path / "specs")
    out_path = tmp_path / "out.md"

    result = route.extract(pdf_path, out_path)

    assert result.status == "extracted"
    assert result.extractor_version == EXTRACTOR_VERSION
    assert result.pages_total == 2
    assert result.pages_kept == 2

    markdown = out_path.read_text(encoding="utf-8")
    assert "CONTEUDO PRINCIPAL DA PAGINA UM" in markdown
    assert "CONTEUDO PRINCIPAL DA PAGINA DOIS" in markdown
    assert "RUBRICA-FULANO" not in markdown


def test_generic_signature_boilerplate_still_removed_without_any_spec_rule(tmp_path: Path):
    pdf_path = _make_pdf(
        tmp_path,
        pages=[
            "CONTEUDO PRINCIPAL\n"
            "Documento assinado digitalmente.\n"
            "Consulte a autenticidade deste documento em"
            " http://sicnet2.aneel.gov.br/sicnetweb/v.aspx,"
            " informando o codigo de verificacao ABCDEF1234567890"
        ],
    )
    route = PdfLlmSpecRoute(generate_fn=_fake_generate_fn(EMPTY_SPEC), spec_cache_dir=tmp_path / "specs")
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    markdown = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "CONTEUDO PRINCIPAL" in markdown
    assert "Documento assinado digitalmente" not in markdown


def test_drop_pages_removes_a_whole_page(tmp_path: Path):
    pdf_path = _make_pdf(
        tmp_path,
        pages=["CONTEUDO DA PAGINA UM", "CONTRATO SOCIAL DA EMPRESA XYZ (anexo completo)"],
    )
    spec = {**EMPTY_SPEC, "drop_pages": [2]}
    route = PdfLlmSpecRoute(generate_fn=_fake_generate_fn(spec), spec_cache_dir=tmp_path / "specs")
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    assert result.pages_total == 2
    assert result.pages_kept == 1
    assert "página(s) descartada" in (result.message or "")
    markdown = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "CONTEUDO DA PAGINA UM" in markdown
    assert "CONTRATO SOCIAL" not in markdown


def test_spec_cache_hit_avoids_a_second_llm_call(tmp_path: Path):
    pdf_path = _make_pdf(tmp_path, pages=["CONTEUDO ESTAVEL QUE PASSA DO LIMITE MINIMO DE CARACTERES"])
    calls: list[str] = []
    spec_cache_dir = tmp_path / "specs"
    route = PdfLlmSpecRoute(
        generate_fn=_fake_generate_fn(EMPTY_SPEC, calls), spec_cache_dir=spec_cache_dir
    )

    route.extract(pdf_path, tmp_path / "out1.md")
    assert len(calls) == 1

    # Same route instance, same document content: second extract() must
    # reuse the persisted spec cache file, never re-invoke generate_fn.
    route.extract(pdf_path, tmp_path / "out2.md")
    assert len(calls) == 1

    cache_files = list(spec_cache_dir.glob("*.json"))
    assert len(cache_files) == 1
    cached = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert cached["model_id"] == "fake-model"
    assert cached["prompt_version"] == PROMPT_VERSION
    assert cached["input_tokens"] == 123
    assert cached["output_tokens"] == 45
    assert cached["cost_usd"] is None  # "fake-model" has no entry in the pricing table


def test_spec_cache_is_content_addressed_so_regenerating_one_document_never_touches_another(
    tmp_path: Path,
):
    pdf_a = _make_pdf(tmp_path, pages=["CONTEUDO PRINCIPAL DO DOCUMENTO A, BEM MAIOR QUE O LIMITE"], name="a")
    pdf_b = _make_pdf(tmp_path, pages=["CONTEUDO PRINCIPAL DO DOCUMENTO B, BEM MAIOR QUE O LIMITE"], name="b")
    calls: list[str] = []
    spec_cache_dir = tmp_path / "specs"
    route = PdfLlmSpecRoute(
        generate_fn=_fake_generate_fn(EMPTY_SPEC, calls), spec_cache_dir=spec_cache_dir
    )

    route.extract(pdf_a, tmp_path / "out_a.md")
    route.extract(pdf_b, tmp_path / "out_b.md")
    assert len(calls) == 2

    cache_files = sorted(spec_cache_dir.glob("*.json"))
    assert len(cache_files) == 2

    # Deleting document A's own cache file must not disturb B's.
    raw_text_a = calls[0]
    key_a = _spec_cache_key(raw_text_a, route.model_id)
    (spec_cache_dir / f"{key_a}.json").unlink()
    remaining = list(spec_cache_dir.glob("*.json"))
    assert len(remaining) == 1

    route.extract(pdf_a, tmp_path / "out_a2.md")
    assert len(calls) == 3  # only A's spec was regenerated
    route.extract(pdf_b, tmp_path / "out_b2.md")
    assert len(calls) == 3  # B's cache entry was untouched


def test_llm_failure_falls_back_to_generic_filter_instead_of_erroring(tmp_path: Path):
    pdf_path = _make_pdf(
        tmp_path,
        pages=[
            "CONTEUDO PRINCIPAL\n"
            "Documento assinado digitalmente.\n"
            "Consulte a autenticidade deste documento em"
            " http://sicnet2.aneel.gov.br/sicnetweb/v.aspx,"
            " informando o codigo de verificacao ABCDEF1234567890"
        ],
    )

    def failing_generate(raw_text: str) -> SpecGenerationResult:
        raise RuntimeError("bedrock indisponível (simulado)")

    route = PdfLlmSpecRoute(generate_fn=failing_generate, spec_cache_dir=tmp_path / "specs")
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    assert "filtro genérico" in (result.message or "")
    markdown = (tmp_path / "out.md").read_text(encoding="utf-8")
    assert "CONTEUDO PRINCIPAL" in markdown
    assert "Documento assinado digitalmente" not in markdown


def test_malformed_llm_spec_also_falls_back_to_generic_filter(tmp_path: Path):
    pdf_path = _make_pdf(tmp_path, pages=["CONTEUDO PRINCIPAL DO DOCUMENTO, BEM MAIOR QUE O LIMITE MINIMO"])

    def bad_generate(raw_text: str) -> SpecGenerationResult:
        return SpecGenerationResult(
            spec={"drop_pages": "not-a-list"},  # invalid shape
            model_id="fake-model",
            region="us-east-1",
            input_tokens=1,
            output_tokens=1,
        )

    route = PdfLlmSpecRoute(generate_fn=bad_generate, spec_cache_dir=tmp_path / "specs")
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "extracted"
    assert "filtro genérico" in (result.message or "")
    assert not list((tmp_path / "specs").glob("*.json"))  # never cached an invalid spec


def test_reports_pending_for_pdf_with_no_extractable_text(tmp_path: Path):
    pdf_path = _make_pdf(tmp_path, pages=["", ""])
    route = PdfLlmSpecRoute(generate_fn=_fake_generate_fn(EMPTY_SPEC), spec_cache_dir=tmp_path / "specs")
    result = route.extract(pdf_path, tmp_path / "out.md")

    assert result.status == "pending"
    assert result.markdown_path is None
    assert "sem camada de texto" in (result.message or "")


def test_can_handle_only_pdf():
    route = PdfLlmSpecRoute(generate_fn=_fake_generate_fn(EMPTY_SPEC))
    assert route.can_handle("pdf") is True
    assert route.can_handle("html") is False
    assert route.can_handle(None) is False


def test_reports_error_when_source_is_not_a_valid_pdf(tmp_path: Path):
    bogus = tmp_path / "not-a-pdf.pdf"
    bogus.write_bytes(b"this is not a pdf file")
    route = PdfLlmSpecRoute(generate_fn=_fake_generate_fn(EMPTY_SPEC), spec_cache_dir=tmp_path / "specs")
    result = route.extract(bogus, tmp_path / "out.md")
    assert result.status == "error"
    assert result.message


def test_estimate_cost_usd_uses_the_pricing_table():
    cost = estimate_cost_usd(
        "us.anthropic.claude-haiku-4-5-20251001-v1:0", input_tokens=1_000_000, output_tokens=1_000_000
    )
    assert cost == pytest.approx(1.00 + 5.00)


def test_estimate_cost_usd_returns_none_for_unknown_model():
    assert estimate_cost_usd("unknown-model", input_tokens=1000, output_tokens=1000) is None
