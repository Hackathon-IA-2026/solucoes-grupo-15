"""CLI entry point for the corpus manifest + batch extraction pipeline
(issue #68).

    python3.12 hackathon/tools/pipeline/cli.py manifest
    python3.12 hackathon/tools/pipeline/cli.py run --categoria "04 Compartilhamento de postes"
    python3.12 hackathon/tools/pipeline/cli.py run --corpus-id case-1-carolina-mmgd

Run from anywhere — paths are resolved relative to the repo root
(`manifest.REPO_ROOT`), the same convention the #59 prototype scripts use.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from executor import BatchExecutor  # noqa: E402
from manifest import (  # noqa: E402
    REPO_ROOT,
    ManifestDocument,
    Sha256Cache,
    build_corpus_manifest,
    compute_corpus_version,
)
from routes import RouteRegistry  # noqa: E402
from routes.pdf_text_generic import PdfTextGenericRoute  # noqa: E402
from triage import apply_triage  # noqa: E402

DEFAULT_DATA_ROOT = REPO_ROOT / "hackathon" / "data"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "hackathon" / ".pipeline-output"


def build_registry() -> RouteRegistry:
    registry = RouteRegistry()
    registry.register(PdfTextGenericRoute())
    return registry


def build_triaged_manifest(
    data_root: Path, output_dir: Path
) -> tuple[list[ManifestDocument], str]:
    sha_cache = Sha256Cache(output_dir / "sha256_cache.json")
    documents = build_corpus_manifest(data_root, sha_cache)
    sha_cache.save()
    documents = apply_triage(documents)
    corpus_version = compute_corpus_version(documents)
    return documents, corpus_version


def write_manifest_json(documents: list[ManifestDocument], corpus_version: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "corpus_version": corpus_version,
        "documentos": [doc.to_dict() for doc in documents],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def cmd_manifest(args: argparse.Namespace) -> None:
    documents, corpus_version = build_triaged_manifest(args.data_root, args.output_dir)
    manifest_path = args.output_dir / "manifest.json"
    write_manifest_json(documents, corpus_version, manifest_path)

    discarded = [doc for doc in documents if doc.descartado]
    pending_no_route = [
        doc for doc in documents if not doc.descartado and doc.sha256 is not None
    ]
    zip_expanded = sum(1 for doc in documents if doc.origem is not None)

    print(f"corpus_version: {corpus_version}")
    print(f"documentos no manifesto: {len(documents)}")
    print(f"  descartados na triagem: {len(discarded)}")
    print(f"  expandidos de zip: {zip_expanded}")
    print(f"manifesto: {manifest_path}")

    by_motivo: dict[str, int] = {}
    for doc in discarded:
        by_motivo[doc.motivo_descarte or ""] = by_motivo.get(doc.motivo_descarte or "", 0) + 1
    for motivo, count in sorted(by_motivo.items(), key=lambda kv: -kv[1]):
        print(f"    {count:5d}  {motivo}")


def _scope_filter(args: argparse.Namespace):
    def scope(doc: ManifestDocument) -> bool:
        if args.corpus_id and doc.corpus_id != args.corpus_id:
            return False
        if args.categoria and doc.categoria != args.categoria:
            return False
        return True

    return scope


def cmd_run(args: argparse.Namespace) -> None:
    documents, corpus_version = build_triaged_manifest(args.data_root, args.output_dir)
    registry = build_registry()
    executor = BatchExecutor(registry, args.output_dir)
    report = executor.run(documents, scope=_scope_filter(args))

    label = args.categoria or args.corpus_id or "corpus-completo"
    report_path = args.output_dir / "reports" / f"{_slug(label)}.jsonl"
    report.write_jsonl(report_path)

    print(f"corpus_version: {corpus_version}")
    print(f"escopo: {label}")
    print(f"documentos processados: {len(report.documents)}")
    print(f"  já em cache (não reprocessados): {report.cached_count()}")
    for status, count in sorted(report.counts().items()):
        print(f"  {status}: {count}")
    print(f"relatório: {report_path}")


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.strip().lower()).strip("-")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest_parser = subparsers.add_parser(
        "manifest", help="build the corpus manifest and print corpus_version"
    )
    manifest_parser.set_defaults(func=cmd_manifest)

    run_parser = subparsers.add_parser(
        "run", help="run the batch executor over a scope of the manifest"
    )
    run_parser.add_argument(
        "--categoria", default=None, help='e.g. "04 Compartilhamento de postes"'
    )
    run_parser.add_argument(
        "--corpus-id", default=None, choices=["processos-aneel", "case-1-carolina-mmgd"]
    )
    run_parser.set_defaults(func=cmd_run)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
