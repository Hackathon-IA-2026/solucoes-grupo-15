"""Corpus-wide scanned-page count (issue #72 acceptance criterion:
"Contagem de documentos/páginas escaneados no corpus completo registrada").

Runs the exact same per-page detection `PdfOcrRoute.extract()` uses
(`routes.pdf_ocr.classify_pdf_pages` — structural full-page-image check +
per-page character-density check, see that module's docstring) over every
non-discarded PDF in the full triaged manifest, **without** calling OCR or
the LLM spec route — this is a detection-only pass, no Bedrock cost, no
Markdown written, per the issue's own instruction ("não precisa rodar OCR
real em todo o corpus, só contar/detectar").

Zip-derived documents are materialized to a temp file the same way
`executor.BatchExecutor._extract` does (reusing its own
`_read_zip_member_bytes`), since `pdfinfo`/`pdftotext`/`pdfimages` need a
real path on disk.

Run with:
    source .env  # AWS creds are NOT needed for this script, but harmless
    python3.12 hackathon/tools/pipeline/scan_corpus_report.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import DEFAULT_DATA_ROOT, DEFAULT_OUTPUT_DIR, build_triaged_manifest  # noqa: E402
from executor import _read_zip_member_bytes  # noqa: E402
from manifest import REPO_ROOT  # noqa: E402
from routes.pdf_ocr import classify_pdf_pages  # noqa: E402


def main() -> int:
    documents, corpus_version = build_triaged_manifest(DEFAULT_DATA_ROOT, DEFAULT_OUTPUT_DIR)
    pdf_docs = [
        doc for doc in documents if not doc.descartado and doc.sha256 is not None and doc.formato == "pdf"
    ]

    total_docs = len(pdf_docs)
    total_pages = 0
    total_scanned_pages = 0
    docs_with_scanned_page = 0
    docs_error = 0
    t0 = time.time()

    for i, doc in enumerate(pdf_docs, start=1):
        tmp_path: Path | None = None
        try:
            if doc.caminho is not None:
                pdf_path = REPO_ROOT / doc.caminho
            else:
                with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    tmp.write(_read_zip_member_bytes(doc))
                pdf_path = tmp_path

            page_count, degraded = classify_pdf_pages(pdf_path)
            total_pages += page_count
            total_scanned_pages += len(degraded)
            if degraded:
                docs_with_scanned_page += 1
        except Exception as exc:
            docs_error += 1
            print(f"  [erro] {doc.caminho or doc.origem}: {exc}", file=sys.stderr)
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

        if i % 200 == 0:
            print(f"  ... {i}/{total_docs} documentos PDF processados ({time.time()-t0:.0f}s)")

    elapsed = time.time() - t0
    print(f"corpus_version: {corpus_version}")
    print(f"documentos PDF (não descartados, com arquivo): {total_docs}")
    print(f"  com falha na inspeção (pdfinfo/pdfimages): {docs_error}")
    print(f"  com pelo menos 1 página escaneada/degradada: {docs_with_scanned_page}")
    print(f"páginas totais nesses documentos: {total_pages}")
    print(f"páginas escaneadas/degradadas (detectadas): {total_scanned_pages}")
    print(f"tempo total de detecção: {elapsed:.1f}s ({elapsed/max(total_docs,1):.2f}s/documento)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
