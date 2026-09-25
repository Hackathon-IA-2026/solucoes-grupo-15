"""PROTOTYPE: assisted downloader for an official SEI/Sicnet process page.

This command opens the public search page in a visible browser and waits for a
saved/exported process page. It exists because SEI/Sicnet may require captcha.
The human solves the captcha; the script handles parsing, grouping and output.
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path

from discover_official_page import discover, resolve_path
from download_families import (
    apply_filters,
    download_all,
    group_by_family,
    load_documents,
    print_plan,
    print_state,
    print_summary,
    write_outputs,
)


SEI_SEARCH_URL = (
    "https://sei.aneel.gov.br/sei/modulos/pesquisa/"
    "md_pesq_processo_pesquisar.php?"
    "acao_externa=protocolo_pesquisar&"
    "acao_origem_externa=protocolo_pesquisar&"
    "id_orgao_acesso_externo=0"
)
SICNET_SEARCH_URL = "https://sicnet2.aneel.gov.br/sicnetweb/pesquisa.asp"


def main() -> int:
    args = parse_args()
    output_root = resolve_path(args.out)
    page_path = resolve_path(args.page)
    manifest_path = output_root / "source_manifest.json"

    if args.open_browser:
        webbrowser.open(search_url(args.source_system))
        print("Browser opened.")
        print("1. Search the process in the official system.")
        print("2. Solve captcha if it appears.")
        print(f"3. Save/copy the final process page to: {page_path}")
        input("Press Enter here after the process page file exists...")

    raw = page_path.read_text(encoding="utf-8")
    manifest = discover(raw, args.source_system, args.family_mode)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    documents = load_documents(manifest_path)
    selected = documents[: args.limit_pieces] if args.limit_pieces else documents
    families = group_by_family(selected)

    print_state("loaded", documents)
    print_state("selected", selected)
    print(f"families selected: {len(families)}")
    print_plan(families)

    if args.dry_run:
        print(f"manifest: {manifest_path}")
        return 0

    results = download_all(families, output_root)
    write_outputs(results, output_root)
    print_summary(results, output_root)
    print(f"source manifest: {manifest_path}")
    ok_statuses = {"downloaded", "metadata_only"}
    return 0 if all(item["status"] in ok_statuses for item in results) else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open SEI/Sicnet and build a family-process download package."
    )
    parser.add_argument(
        "--source-system",
        default="sei",
        choices=["sei", "sicnet2"],
        help="Official source to open and parse.",
    )
    parser.add_argument(
        "--page",
        required=True,
        help="Saved/exported HTML, Markdown or text of the final process page.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Scratch output directory for manifest, files and timeline.",
    )
    parser.add_argument(
        "--family-mode",
        default="process",
        choices=["process", "protocol"],
        help="Use process for Carolina-style families; protocol for one family per row.",
    )
    parser.add_argument(
        "--limit-pieces",
        type=int,
        default=0,
        help="Optional limit of pieces/protocols inside the family.",
    )
    parser.add_argument(
        "--no-open-browser",
        dest="open_browser",
        action="store_false",
        help="Do not open the official search page; only parse the provided file.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print the plan.")
    parser.set_defaults(open_browser=True)
    return parser.parse_args()


def search_url(source_system: str) -> str:
    if source_system == "sicnet2":
        return SICNET_SEARCH_URL
    return SEI_SEARCH_URL


if __name__ == "__main__":
    raise SystemExit(main())
