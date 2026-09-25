"""PROTOTYPE: terminal downloader for document families.

This is intentionally manifest-driven. SEI/Sicnet scrapers can later become
manifest producers while this grouping/downloading shape stays stable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class SourceDocument:
    family_id: str
    family_label: str
    document_type: str
    official_identifier: str
    process_number: str
    source_system: str
    version_id: str
    version_date: str
    version_date_source: str
    locator: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SourceDocument":
        required = {
            "family_id",
            "family_label",
            "document_type",
            "official_identifier",
            "process_number",
            "source_system",
            "version_id",
            "version_date",
            "version_date_source",
            "locator",
        }
        missing = sorted(required - set(raw))
        if missing:
            raise ValueError(f"document missing required fields: {', '.join(missing)}")
        return cls(**{key: str(raw[key]) for key in required})

    def searchable_text(self) -> str:
        return " ".join(
            [
                self.family_id,
                self.family_label,
                self.document_type,
                self.official_identifier,
                self.process_number,
                self.source_system,
                self.version_id,
                self.locator,
            ]
        ).lower()


def main() -> int:
    args = parse_args()
    manifest_path = resolve_path(args.manifest)
    output_root = resolve_path(args.out)

    documents = load_documents(manifest_path)
    selected = apply_filters(documents, args)
    selected = selected[: args.limit] if args.limit else selected
    families = group_by_family(selected)

    print_state("loaded", documents)
    print_state("selected", selected)
    print(f"families selected: {len(families)}")

    if args.dry_run:
        print_plan(families)
        return 0

    output_root.mkdir(parents=True, exist_ok=True)
    results = download_all(families, output_root)
    write_outputs(results, output_root)
    print_summary(results, output_root)
    return 0 if all(item["status"] == "downloaded" for item in results) else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PROTOTYPE downloader that groups PDFs as document families."
    )
    parser.add_argument("--manifest", required=True, help="Path to source manifest JSON.")
    parser.add_argument(
        "--out",
        default="hackathon/.prototype-downloads/families",
        help="Scratch output directory.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print the plan.")
    parser.add_argument("--process", action="append", default=[], help="Process filter.")
    parser.add_argument("--type", action="append", default=[], help="Document type filter.")
    parser.add_argument("--family", action="append", default=[], help="Family id filter.")
    parser.add_argument(
        "--source-system",
        action="append",
        default=[],
        help="Source system filter, e.g. sei or sicnet2.",
    )
    parser.add_argument("--query", action="append", default=[], help="Free text filter.")
    parser.add_argument("--limit", type=int, default=0, help="Limit selected versions.")
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def load_documents(manifest_path: Path) -> list[SourceDocument]:
    with manifest_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    docs = raw.get("documents")
    if not isinstance(docs, list):
        raise ValueError("manifest must contain a documents list")
    return [SourceDocument.from_dict(item) for item in docs]


def apply_filters(
    documents: list[SourceDocument], args: argparse.Namespace
) -> list[SourceDocument]:
    selected = documents
    selected = filter_any(selected, args.process, lambda doc: doc.process_number)
    selected = filter_any(selected, args.type, lambda doc: doc.document_type)
    selected = filter_any(selected, args.family, lambda doc: doc.family_id)
    selected = filter_any(selected, args.source_system, lambda doc: doc.source_system)
    for query in args.query:
        needle = query.lower()
        selected = [doc for doc in selected if needle in doc.searchable_text()]
    return selected


def filter_any(
    documents: list[SourceDocument], values: list[str], getter: Any
) -> list[SourceDocument]:
    if not values:
        return documents
    wanted = {value.lower() for value in values}
    return [doc for doc in documents if getter(doc).lower() in wanted]


def group_by_family(
    documents: list[SourceDocument],
) -> dict[str, list[SourceDocument]]:
    families: dict[str, list[SourceDocument]] = {}
    for doc in documents:
        families.setdefault(doc.family_id, []).append(doc)
    for versions in families.values():
        versions.sort(key=lambda doc: doc.version_date, reverse=True)
    return dict(sorted(families.items()))


def print_state(label: str, documents: list[SourceDocument]) -> None:
    print(f"{label}: {len(documents)} versions")


def print_plan(families: dict[str, list[SourceDocument]]) -> None:
    print("\nplan:")
    for family_id, versions in families.items():
        face = versions[0]
        print(f"- {family_id} | {face.family_label} | {len(versions)} version(s)")
        for version in versions:
            print(
                "  "
                f"{version.version_date} | {version.document_type} | "
                f"{version.process_number} | {version.locator}"
            )


def download_all(
    families: dict[str, list[SourceDocument]], output_root: Path
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for family_id, versions in families.items():
        for version in versions:
            results.append(download_one(family_id, version, output_root))
    return results


def download_one(
    family_id: str, version: SourceDocument, output_root: Path
) -> dict[str, Any]:
    target_dir = output_root / "families" / safe_name(family_id) / "versions" / safe_name(
        version.version_id
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / source_filename(version.locator)

    try:
        if version.locator.startswith(("http://", "https://")):
            download_url(version.locator, target_path)
        else:
            source_path = resolve_path(version.locator)
            shutil.copy2(source_path, target_path)
        digest = sha256_file(target_path)
        status = "downloaded"
        error = None
        size_bytes = target_path.stat().st_size
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        status = "failed"
        error = str(exc)
        digest = None
        size_bytes = 0

    return {
        "status": status,
        "error": error,
        "family_id": family_id,
        "family_label": version.family_label,
        "document_type": version.document_type,
        "official_identifier": version.official_identifier,
        "process_number": version.process_number,
        "source_system": version.source_system,
        "version_id": version.version_id,
        "version_date": version.version_date,
        "version_date_source": version.version_date_source,
        "source_locator": version.locator,
        "stored_path": str(target_path.relative_to(output_root)),
        "sha256": digest,
        "size_bytes": size_bytes,
    }


def source_filename(locator: str) -> str:
    if locator.startswith(("http://", "https://")):
        name = Path(urllib.parse.urlparse(locator).path).name
        return safe_name(name or "document.pdf")
    return safe_name(Path(locator).name)


def download_url(url: str, target_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "CapiWattLensPrototype/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        with target_path.open("wb") as handle:
            shutil.copyfileobj(response, handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    allowed = []
    for char in value.strip():
        if char.isalnum() or char in {".", "-", "_"}:
            allowed.append(char)
        else:
            allowed.append("-")
    safe = "".join(allowed).strip(".-")
    return safe or "item"


def write_outputs(results: list[dict[str, Any]], output_root: Path) -> None:
    manifest = {
        "schema_version": "prototype-downloader-output-v1",
        "families": build_manifest_families(results),
        "versions": results,
    }
    (output_root / "download_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_root / "timeline.md").write_text(build_timeline(results), encoding="utf-8")


def build_manifest_families(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for item in results:
        family = families.setdefault(
            item["family_id"],
            {
                "family_id": item["family_id"],
                "family_label": item["family_label"],
                "document_type": item["document_type"],
                "versions": [],
            },
        )
        family["versions"].append(
            {
                "version_id": item["version_id"],
                "version_date": item["version_date"],
                "status": item["status"],
                "stored_path": item["stored_path"],
                "sha256": item["sha256"],
            }
        )
    for family in families.values():
        family["versions"].sort(key=lambda item: item["version_date"], reverse=True)
    return list(families.values())


def build_timeline(results: list[dict[str, Any]]) -> str:
    families: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        families.setdefault(item["family_id"], []).append(item)
    lines = ["# Prototype download timeline", ""]
    for family_id in sorted(families):
        versions = sorted(
            families[family_id], key=lambda item: item["version_date"], reverse=True
        )
        lines.append(f"## {family_id}")
        lines.append("")
        lines.append(f"Family: {versions[0]['family_label']}")
        lines.append("")
        for item in versions:
            lines.append(
                "- "
                f"{item['version_date']} | {item['version_id']} | "
                f"{item['process_number']} | {item['status']} | {item['stored_path']}"
            )
        lines.append("")
    return "\n".join(lines)


def print_summary(results: list[dict[str, Any]], output_root: Path) -> None:
    ok = sum(1 for item in results if item["status"] == "downloaded")
    failed = len(results) - ok
    print(f"\ndownloaded: {ok}")
    print(f"failed: {failed}")
    print(f"output: {output_root}")
    print(f"manifest: {output_root / 'download_manifest.json'}")
    print(f"timeline: {output_root / 'timeline.md'}")
    for item in results:
        if item["status"] == "failed":
            print(f"failed: {item['version_id']} - {item['error']}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
