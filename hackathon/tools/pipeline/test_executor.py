"""Unit tests for executor.py (issue #68): resumable batch execution, cache
keyed by (sha256, extractor_version), and the report never silently
swallowing a document.

Uses a `FakeRoute` stub instead of real PDFs — the resumability/caching
mechanics under test are format-agnostic; `test_routes_pdf_text_generic.py`
already covers the real PDF route's own behavior.

Run with: python3.12 -m pytest hackathon/tools/pipeline/test_executor.py -q
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from executor import BatchExecutor
from manifest import ManifestDocument
from routes import ExtractionResult, RouteRegistry


@dataclass
class FakeRoute:
    name: str = "fake_pdf"
    extractor_version: str = "fake_pdf@1"
    formats: tuple[str, ...] = ("pdf",)
    calls: list[Path] = field(default_factory=list)

    def can_handle(self, formato: str | None) -> bool:
        return formato in self.formats

    def extract(self, source_path: Path, out_path: Path) -> ExtractionResult:
        self.calls.append(source_path)
        content = source_path.read_bytes()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(f"<!-- page:1 -->\n{content!r}\n", encoding="utf-8")
        return ExtractionResult(
            status="extracted",
            extractor_version=self.extractor_version,
            route=self.name,
            markdown_path=out_path,
            pages_total=1,
            pages_kept=1,
            percent_removed=0.0,
        )


def _doc(**overrides) -> ManifestDocument:
    base = dict(
        corpus_id="processos-aneel",
        categoria="04 Compartilhamento de postes",
        processo="48500.000000/2026-00",
        numero_sei="0000000",
        tipo_documento="Carta",
        data="01/01/2026",
        caminho="data/doc.pdf",
        formato="pdf",
        bytes=10,
        sha256="f" * 64,
        status_origem="ok",
    )
    base.update(overrides)
    return ManifestDocument(**base)


def test_discarded_document_is_reported_not_processed(tmp_path: Path):
    route = FakeRoute()
    executor = BatchExecutor(RouteRegistry([route]), tmp_path)
    doc = _doc(descartado=True, motivo_descarte="recibo, sem valor de busca")

    report = executor.run([doc])

    assert len(report.documents) == 1
    assert report.documents[0].status == "descartado"
    assert report.documents[0].message == "recibo, sem valor de busca"
    assert route.calls == []


def test_restrito_document_is_pending_not_error(tmp_path: Path):
    executor = BatchExecutor(RouteRegistry([FakeRoute()]), tmp_path)
    doc = _doc(caminho=None, sha256=None, formato=None, status_origem="restrito")

    report = executor.run([doc])

    assert report.documents[0].status == "pending"
    assert "restrito" in report.documents[0].message


def test_format_with_no_registered_route_is_pending_not_silently_dropped(tmp_path: Path):
    executor = BatchExecutor(RouteRegistry([FakeRoute()]), tmp_path)  # only handles "pdf"
    doc = _doc(formato="html", caminho="data/doc.html")

    report = executor.run([doc])

    assert len(report.documents) == 1  # never silently dropped
    assert report.documents[0].status == "pending"
    assert "sem rota" in report.documents[0].message


def test_second_run_hits_cache_and_never_calls_extract_again(tmp_path: Path, monkeypatch):
    source_dir = tmp_path / "repo"
    source_dir.mkdir()
    source = source_dir / "source.pdf"
    source.write_bytes(b"%PDF-fake-content")

    import executor as executor_module

    monkeypatch.setattr(executor_module, "REPO_ROOT", source_dir)

    route = FakeRoute()
    batch_executor = BatchExecutor(RouteRegistry([route]), tmp_path / "out")
    doc = _doc(caminho="source.pdf")

    first = batch_executor.run([doc])
    assert first.documents[0].status == "extracted"
    assert first.documents[0].cached is False
    assert len(route.calls) == 1

    second = batch_executor.run([doc])
    assert second.documents[0].status == "extracted"
    assert second.documents[0].cached is True
    assert len(route.calls) == 1  # not called again


def test_different_extractor_version_is_not_served_from_old_cache(tmp_path: Path, monkeypatch):
    source_dir = tmp_path / "repo"
    source_dir.mkdir()
    source = source_dir / "source.pdf"
    source.write_bytes(b"%PDF-fake-content")

    import executor as executor_module

    monkeypatch.setattr(executor_module, "REPO_ROOT", source_dir)

    route_v1 = FakeRoute(extractor_version="fake_pdf@1")
    doc = _doc(caminho="source.pdf")
    BatchExecutor(RouteRegistry([route_v1]), tmp_path / "out").run([doc])

    route_v2 = FakeRoute(extractor_version="fake_pdf@2")
    second_report = BatchExecutor(RouteRegistry([route_v2]), tmp_path / "out").run([doc])

    assert second_report.documents[0].cached is False
    assert len(route_v2.calls) == 1


def test_zip_derived_document_is_materialized_from_the_zip_before_extraction(
    tmp_path: Path, monkeypatch
):
    source_dir = tmp_path / "repo"
    source_dir.mkdir()
    zip_path = source_dir / "anexo.zip"
    member_content = b"%PDF-inside-zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("membro.pdf", member_content)

    import executor as executor_module
    import hashlib

    monkeypatch.setattr(executor_module, "REPO_ROOT", source_dir)

    route = FakeRoute()
    batch_executor = BatchExecutor(RouteRegistry([route]), tmp_path / "out")
    doc = _doc(
        caminho=None,
        sha256=hashlib.sha256(member_content).hexdigest(),
        formato="pdf",
        origem={"zip_caminho": "anexo.zip", "zip_membro": "membro.pdf", "profundidade": 1},
    )

    report = batch_executor.run([doc])

    assert report.documents[0].status == "extracted"
    assert len(route.calls) == 1
    # the materialized temp file actually held the zip member's bytes
    markdown = Path(report.documents[0].markdown_path).read_text(encoding="utf-8")
    assert repr(member_content) in markdown


def test_report_jsonl_round_trips(tmp_path: Path):
    executor = BatchExecutor(RouteRegistry([FakeRoute()]), tmp_path / "out")
    doc = _doc(descartado=True, motivo_descarte="teste")
    report = executor.run([doc])
    report_path = tmp_path / "report.jsonl"
    report.write_jsonl(report_path)

    import json

    lines = report_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["status"] == "descartado"
    assert parsed["motivo_descarte"] == "teste"
