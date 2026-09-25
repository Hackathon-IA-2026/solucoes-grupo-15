"""PROTOTYPE: assisted batch downloader for the first N process families.

The command does not bypass captcha. It opens the official search page, asks the
human to save/export the results page, extracts process numbers, then asks for
the selected process pages and builds one collection family per process.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from assisted_process_downloader import search_url
from discover_official_page import LinkTextParser, discover, resolve_path, slug
from download_families import (
    download_all,
    group_by_family,
    print_plan,
    print_summary,
    print_state,
    write_outputs,
)


PROCESS_RE = re.compile(r"[0-9]{5}\.[0-9]{6}/[0-9]{4}-[0-9]{2}")


@dataclass(frozen=True)
class ProcessHit:
    process_number: str
    href: str | None = None


def main() -> int:
    args = parse_args()
    output_root = resolve_path(args.out)
    results_page = resolve_path(args.results_page)
    pages_dir = resolve_path(args.pages_dir)

    if args.open_browser:
        webbrowser.open(search_url(args.source_system))
        print("Browser opened.")
        print("Fill the official search with:")
        print(f"- theme: {args.theme}")
        print(f"- date from: {args.date_from}")
        print(f"- date to: {args.date_to}")
        print("Solve captcha if it appears, run the search, then save/copy the results page.")
        print(f"Expected results page file: {results_page}")
        input("Press Enter here after the results page file exists...")

    hits = parse_results_page(results_page)
    selected_hits = hits[: args.limit_families]
    if not selected_hits:
        raise SystemExit(f"No process numbers found in {results_page}")

    output_root.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    print(f"processes found: {len(hits)}")
    print(f"families selected: {len(selected_hits)}")
    for index, hit in enumerate(selected_hits, start=1):
        print(f"{index}. {hit.process_number}")

    manifests = []
    for hit in selected_hits:
        page_path = process_page_path(pages_dir, hit.process_number)
        if not page_path.exists():
            if hit.href:
                webbrowser.open(hit.href)
            print("")
            print(f"Save/copy the process page for {hit.process_number} to:")
            print(page_path)
            input("Press Enter here after the process page file exists...")
        raw = page_path.read_text(encoding="utf-8")
        manifests.append(discover(raw, args.source_system, "process"))

    combined = combine_manifests(manifests, args)
    source_manifest = output_root / "source_manifest.json"
    source_manifest.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    documents = documents_from_manifest(combined)
    families = group_by_family(documents)
    print_state("loaded", documents)
    print_state("selected", documents)
    print(f"families selected: {len(families)}")
    print_plan(families)

    if args.dry_run:
        print(f"source manifest: {source_manifest}")
        return 0

    results = download_all(families, output_root)
    write_outputs(results, output_root)
    print_summary(results, output_root)
    print(f"source manifest: {source_manifest}")
    ok_statuses = {"downloaded", "metadata_only"}
    return 0 if all(item["status"] in ok_statuses for item in results) else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect the first N process families from a saved results page."
    )
    parser.add_argument(
        "--source-system",
        default="sei",
        choices=["sei", "sicnet2"],
        help="Official source to open and parse.",
    )
    parser.add_argument("--theme", required=True, help="Theme/filter used in the search.")
    parser.add_argument("--date-from", required=True, help="Search start date.")
    parser.add_argument("--date-to", required=True, help="Search end date.")
    parser.add_argument(
        "--limit-families",
        type=int,
        default=3,
        help="How many process families to collect from the results.",
    )
    parser.add_argument(
        "--results-page",
        required=True,
        help="Saved/exported HTML, Markdown or text with the search results.",
    )
    parser.add_argument(
        "--pages-dir",
        required=True,
        help="Directory containing/saving one process page per selected process.",
    )
    parser.add_argument("--out", required=True, help="Output directory.")
    parser.add_argument(
        "--no-open-browser",
        dest="open_browser",
        action="store_false",
        help="Do not open the official search page; only parse saved files.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print the plan.")
    parser.set_defaults(open_browser=True)
    return parser.parse_args()


def parse_results_page(path: Path) -> list[ProcessHit]:
    raw = path.read_text(encoding="utf-8")
    text, links = normalize_with_links(raw)
    hits_by_process: dict[str, ProcessHit] = {}

    for process_number in PROCESS_RE.findall(text):
        hits_by_process.setdefault(
            process_number, ProcessHit(process_number, links.get(process_number))
        )
    for label, href in links.items():
        for process_number in PROCESS_RE.findall(label):
            hits_by_process.setdefault(process_number, ProcessHit(process_number, href))

    return list(hits_by_process.values())


def normalize_with_links(raw: str) -> tuple[str, dict[str, str]]:
    parser = LinkTextParser()
    parser.feed(raw)
    if parser.text_parts:
        text = parser.text()
        links = parser.links
    else:
        text = raw
        links = {}
    return html.unescape(text).replace("\xa0", " "), links


def process_page_path(pages_dir: Path, process_number: str) -> Path:
    safe = slug(process_number).replace("_", "-")
    for suffix in (".html", ".htm", ".md", ".txt"):
        candidate = pages_dir / f"{safe}{suffix}"
        if candidate.exists():
            return candidate
    return pages_dir / f"{safe}.html"


def combine_manifests(manifests: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    documents = []
    processes = []
    for manifest in manifests:
        processes.append(manifest.get("process_number"))
        documents.extend(manifest.get("documents", []))
    return {
        "schema_version": "prototype-document-downloader-v1",
        "generated_from": "assisted_batch",
        "source_system": args.source_system,
        "family_mode": "process",
        "theme": args.theme,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "limit_families": args.limit_families,
        "processes": processes,
        "documents": documents,
    }


def documents_from_manifest(manifest: dict[str, Any]) -> list[Any]:
    from download_families import SourceDocument

    return [SourceDocument.from_dict(item) for item in manifest["documents"]]


if __name__ == "__main__":
    raise SystemExit(main())
