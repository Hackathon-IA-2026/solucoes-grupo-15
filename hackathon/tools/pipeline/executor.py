"""Resumable batch executor (issue #68): dispatches every non-discarded
manifest document to a route (`routes/`) and reports the outcome, without
ever redoing work already cached.

## Cache

Keyed by `(sha256, extractor_version)` — exactly the pair issue #68 names.
Two different source files with the same content (same `sha256`) share a
cache entry and its Markdown output; the same file re-run through a bumped
`extractor_version` gets a fresh entry, never a stale hit. Cache entries are
small JSON sidecars under `<output_dir>/cache/`; the Markdown itself lives
under `<output_dir>/markdown/`, named by the same `(sha256,
extractor_version)` pair so the two can never point at each other
incorrectly.

Both directories are outside the git tree (`<output_dir>` defaults to
`hackathon/.pipeline-output/`, gitignored — see `cli.py`) — the corpus
itself is not versioned (issue #56/#68), and neither is its extraction
output; external storage for it is a separate, still-open concern (I4).

## Report

One :class:`DocumentReport` per manifest document actually considered
(discarded documents are reported too, with `status="descartado"` — never
silently skipped). `status="pending"` covers every document that a route
never got to produce Markdown for a legitimate, documented reason: no route
claims its format (e.g. HTML, until #70 lands), a PDF with no usable text
layer (candidate for #72's OCR route), or a document ANEEL never made
downloadable (`status_origem == "restrito"`). `status="error"` is reserved
for a route that was supposed to handle the format and failed unexpectedly
(e.g. `pdftotext`/`pdfinfo` crashing) — never used for "no route exists".
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from manifest import ManifestDocument, REPO_ROOT
from routes import ExtractionResult, RouteRegistry


@dataclass
class DocumentReport:
    corpus_id: str
    categoria: str | None
    processo: str
    caminho: str | None
    sha256: str | None
    formato: str | None
    tipo_documento: str
    descartado: bool
    motivo_descarte: str | None
    route: str | None
    extractor_version: str | None
    status: str  # "extracted" | "pending" | "error" | "descartado"
    cached: bool
    pages_total: int | None = None
    pages_kept: int | None = None
    percent_removed: float | None = None
    markdown_path: str | None = None
    message: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BatchReport:
    documents: list[DocumentReport]

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for doc in self.documents:
            counts[doc.status] = counts.get(doc.status, 0) + 1
        return counts

    def cached_count(self) -> int:
        return sum(1 for doc in self.documents if doc.cached)

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for doc in self.documents:
                handle.write(json.dumps(doc.to_dict(), ensure_ascii=False) + "\n")


class BatchExecutor:
    def __init__(self, registry: RouteRegistry, output_dir: Path):
        self.registry = registry
        self.output_dir = output_dir
        self.markdown_dir = output_dir / "markdown"
        self.cache_dir = output_dir / "cache"

    def run(
        self,
        documents: Iterable[ManifestDocument],
        scope: Callable[[ManifestDocument], bool] | None = None,
    ) -> BatchReport:
        reports: list[DocumentReport] = []
        for doc in documents:
            if scope is not None and not scope(doc):
                continue
            reports.append(self._process(doc))
        return BatchReport(reports)

    def _process(self, doc: ManifestDocument) -> DocumentReport:
        base = {
            "corpus_id": doc.corpus_id,
            "categoria": doc.categoria,
            "processo": doc.processo,
            "caminho": doc.caminho,
            "sha256": doc.sha256,
            "formato": doc.formato,
            "tipo_documento": doc.tipo_documento,
            "descartado": doc.descartado,
            "motivo_descarte": doc.motivo_descarte,
        }

        if doc.descartado:
            return DocumentReport(
                **base,
                route=None,
                extractor_version=None,
                status="descartado",
                cached=False,
                message=doc.motivo_descarte,
            )

        if doc.sha256 is None:
            return DocumentReport(
                **base,
                route=None,
                extractor_version=None,
                status="pending",
                cached=False,
                message=f"documento sem arquivo local (status_origem={doc.status_origem!r})",
            )

        route = self.registry.dispatch(doc.formato)
        if route is None:
            return DocumentReport(
                **base,
                route=None,
                extractor_version=None,
                status="pending",
                cached=False,
                message=f"sem rota de extração para o formato {doc.formato!r}",
            )

        cache_path = self._cache_path(doc.sha256, route.extractor_version)
        cached_result = self._read_cache(cache_path)
        if cached_result is not None:
            return DocumentReport(
                **base,
                route=route.name,
                extractor_version=route.extractor_version,
                cached=True,
                **cached_result,
            )

        result = self._extract(doc, route)
        self._write_cache(cache_path, result)
        return DocumentReport(
            **base,
            route=route.name,
            extractor_version=route.extractor_version,
            cached=False,
            status=result.status,
            pages_total=result.pages_total,
            pages_kept=result.pages_kept,
            percent_removed=result.percent_removed,
            markdown_path=str(result.markdown_path) if result.markdown_path else None,
            message=result.message,
        )

    def _extract(self, doc: ManifestDocument, route) -> ExtractionResult:
        out_path = self.markdown_dir / f"{doc.sha256}__{route.extractor_version}.md"
        if doc.caminho is not None:
            return route.extract(REPO_ROOT / doc.caminho, out_path)

        # zip-derived document: materialize the member to a temp file, since
        # extraction routes work off a real path on disk (pdftotext etc.).
        suffix = f".{doc.formato}" if doc.formato else ""
        with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(_read_zip_member_bytes(doc))
        try:
            return route.extract(tmp_path, out_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _cache_path(self, sha256: str, extractor_version: str) -> Path:
        return self.cache_dir / f"{sha256}__{extractor_version}.json"

    def _read_cache(self, cache_path: Path) -> dict | None:
        if not cache_path.exists():
            return None
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        markdown_path = data.get("markdown_path")
        if markdown_path and not Path(markdown_path).exists():
            # Cache metadata survived but the Markdown didn't (output dir
            # partially cleaned) — do not report a cache hit for output
            # that no longer exists.
            return None
        return data

    def _write_cache(self, cache_path: Path, result: ExtractionResult) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "status": result.status,
            "pages_total": result.pages_total,
            "pages_kept": result.pages_kept,
            "percent_removed": result.percent_removed,
            "markdown_path": str(result.markdown_path) if result.markdown_path else None,
            "message": result.message,
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _read_zip_member_bytes(doc: ManifestDocument) -> bytes:
    origem = doc.origem
    if origem is None:
        raise ValueError(f"documento sem caminho e sem origem de zip: {doc!r}")

    lineage: list[str] = origem.get("zip_lineage") or [origem["zip_caminho"]]
    outer_path = REPO_ROOT / lineage[0]
    with zipfile.ZipFile(outer_path) as zf:
        data = None
        current_zf = zf
        opened: list[zipfile.ZipFile] = []
        try:
            for member_name in lineage[1:]:
                data = current_zf.read(member_name)
                current_zf = zipfile.ZipFile(io.BytesIO(data))
                opened.append(current_zf)
            return current_zf.read(origem["zip_membro"])
        finally:
            for zf_opened in opened:
                zf_opened.close()
