"""Extraction route contract (issue #68) — the plug point future tickets
(#70 HTML, #71 PDF+LLM specs, #72 OCR) implement against, without touching
`executor.py`.

A **route** takes one :class:`~manifest.ManifestDocument` and produces
Markdown with page markers, or reports why it could not (see
:class:`ExtractionResult`). Nothing about a route is executor-specific: it
does not know about caching, resuming, or reporting — `executor.py` is the
only thing that reads `extractor_version`/`sha256` for caching purposes.

## Contract

- **Entrada**: one `ManifestDocument` with a real `caminho` on disk (the
  executor never calls a route for a document with `caminho is None`, e.g.
  `status_origem == "restrito"`, and never for a `descartado` document).
- **Saída**: Markdown text with page markers, `<!-- page:N -->` before each
  page's content — the same marker format
  `hackathon/tools/prototypes/pdf_to_markdown/filter_verbatim.py` writes
  (issue #59). A route with no natural notion of pages (HTML, issue #70)
  must still document, in its own module docstring, what it puts in that
  single marker (e.g. `<!-- page:1 -->` for the whole document).
- **Identidade da versão extraída**: `(sha256, extractor_version)`. Two
  different extractor versions of the same source document, or the same
  extractor version applied to two source documents with the same content
  hash, are exactly the cache keys `executor.py` uses — a route must bump
  its own `extractor_version` string whenever its output for the same input
  would change (new regex, new dependency version with different output,
  etc.), so stale cache entries are never served silently.
- **`can_handle`**: a cheap, format-only pre-check (e.g. "is this a PDF"),
  never one that requires doing the extraction work to answer. A route may
  still discover *inside* `extract()` that it cannot actually produce
  useful output (e.g. a PDF with no extractable text layer) — that is a
  `status="pending"` result, never an exception and never a silent
  `status="extracted"` with empty content.
- **Dispatch is by format only** (`ManifestDocument.formato`), first
  matching route in `RouteRegistry` order wins. A document whose format no
  registered route claims is `status="pending"`, reason
  `"sem rota para o formato <formato>"` — reported, not swallowed
  (acceptance criterion of issue #68).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

Status = Literal["extracted", "pending", "error"]


@dataclass
class ExtractionResult:
    status: Status
    extractor_version: str
    route: str
    markdown_path: Path | None = None
    pages_total: int | None = None
    pages_kept: int | None = None
    percent_removed: float | None = None
    message: str | None = None


class ExtractionRoute(Protocol):
    name: str
    extractor_version: str

    def can_handle(self, formato: str | None) -> bool: ...

    def extract(self, source_path: Path, out_path: Path) -> ExtractionResult: ...


class RouteRegistry:
    """Ordered list of routes; first `can_handle` match wins."""

    def __init__(self, routes: list[ExtractionRoute] | None = None):
        self._routes: list[ExtractionRoute] = list(routes) if routes else []

    def register(self, route: ExtractionRoute) -> None:
        self._routes.append(route)

    def dispatch(self, formato: str | None) -> ExtractionRoute | None:
        for route in self._routes:
            if route.can_handle(formato):
                return route
        return None

    def __iter__(self):
        return iter(self._routes)
