"""PROTOTYPE: build a downloader manifest from an official process page.

The script accepts HTML, Markdown, or plain text exported/copied from SEI/Sicnet.
It does not bypass captcha. Use it after opening the public page normally and
saving/copying the process page contents.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class ProtocolRow:
    protocol_number: str
    document_type: str
    document_date: str
    inclusion_date: str
    unit: str
    href: str | None = None


class LinkTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._href_stack: list[str | None] = []
        self.links: dict[str, str] = {}
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href") if tag.lower() == "a" else None
        self._href_stack.append(href)

    def handle_endtag(self, tag: str) -> None:
        if self._href_stack:
            self._href_stack.pop()

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        self.text_parts.append(value)
        href = next((item for item in reversed(self._href_stack) if item), None)
        if href:
            self.links[value] = href

    def text(self) -> str:
        return "\n".join(self.text_parts)


def main() -> int:
    args = parse_args()
    input_path = resolve_path(args.input)
    output_path = resolve_path(args.out)
    raw = input_path.read_text(encoding="utf-8")
    manifest = discover(raw, args.source_system)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"process: {manifest.get('process_number', 'unknown')}")
    print(f"documents: {len(manifest['documents'])}")
    print(f"families: {len({item['family_id'] for item in manifest['documents']})}")
    print(f"manifest: {output_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a CapiWatt downloader manifest from a saved official page."
    )
    parser.add_argument("--input", required=True, help="Saved HTML/Markdown/text page.")
    parser.add_argument("--out", required=True, help="Output manifest JSON.")
    parser.add_argument(
        "--source-system",
        default="sei",
        choices=["sei", "sicnet2"],
        help="Official source represented by the page.",
    )
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def discover(raw: str, source_system: str) -> dict[str, Any]:
    text, links = normalize_input(raw)
    process_number = (
        first_table_value(raw, "Processo")
        or first_match(r"Processo:\s*([0-9]{5}\.[0-9]{6}/[0-9]{4}-[0-9]{2})", text)
    )
    process_type = first_table_value(raw, "Tipo") or first_match(r"Tipo:\s*(.+)", text) or ""
    generated_at = first_table_value(raw, "Data de Geracao") or first_table_value(
        raw, "Data de Geração"
    ) or first_match(
        r"Data de Gera[cç][aã]o:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text
    )
    protocols = parse_protocol_rows(raw, text, links)
    documents = [
        protocol_to_document(row, process_number, source_system) for row in protocols
    ]
    return {
        "schema_version": "prototype-document-downloader-v1",
        "generated_from": "official_page_export",
        "source_system": source_system,
        "process_number": process_number,
        "process_type": process_type,
        "generated_at": generated_at,
        "documents": documents,
    }


def normalize_input(raw: str) -> tuple[str, dict[str, str]]:
    parser = LinkTextParser()
    parser.feed(raw)
    if parser.text_parts:
        text = parser.text()
        links = parser.links
    else:
        text = raw
        links = {}
    text = html.unescape(text).replace("\xa0", " ")
    return text, links


def first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def first_table_value(raw: str, label: str) -> str | None:
    normalized_label = slug(label).replace("_", "")
    for line in raw.splitlines():
        if "|" not in line:
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) < 2:
            continue
        left = slug(columns[0]).replace("_", "")
        if left.rstrip(":") == normalized_label:
            return columns[1].strip() or None
    return None


def parse_protocol_rows(
    raw: str, text: str, links: dict[str, str]
) -> list[ProtocolRow]:
    markdown_rows = parse_markdown_protocol_rows(raw, links)
    if markdown_rows:
        return markdown_rows
    return parse_text_protocol_rows(text, links)


def parse_markdown_protocol_rows(raw: str, links: dict[str, str]) -> list[ProtocolRow]:
    rows: list[ProtocolRow] = []
    for line in raw.splitlines():
        if "|" not in line:
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) < 5:
            continue
        if not re.fullmatch(r"[0-9]{5,}", columns[0]):
            continue
        rows.append(
            ProtocolRow(
                protocol_number=columns[0],
                document_type=columns[1],
                document_date=columns[2],
                inclusion_date=columns[3],
                unit=columns[4],
                href=links.get(columns[0]),
            )
        )
    return rows


def parse_text_protocol_rows(text: str, links: dict[str, str]) -> list[ProtocolRow]:
    pattern = re.compile(
        r"(?P<protocol>[0-9]{5,})\s+"
        r"(?P<type>.+?)\s+"
        r"(?P<doc_date>[0-9]{2}/[0-9]{2}/[0-9]{4})\s+"
        r"(?P<inclusion>[0-9]{2}/[0-9]{2}/[0-9]{4})\s+"
        r"(?P<unit>[A-Z0-9_-]+)",
        flags=re.MULTILINE,
    )
    rows = []
    for match in pattern.finditer(text):
        protocol = match.group("protocol")
        rows.append(
            ProtocolRow(
                protocol_number=protocol,
                document_type=match.group("type").strip(),
                document_date=match.group("doc_date"),
                inclusion_date=match.group("inclusion"),
                unit=match.group("unit").strip(),
                href=links.get(protocol),
            )
        )
    return rows


def protocol_to_document(
    row: ProtocolRow, process_number: str | None, source_system: str
) -> dict[str, str]:
    family_id = f"{source_system}-{row.protocol_number}"
    process_label = process_number or "processo-desconhecido"
    locator = row.href or f"missing://{source_system}/{row.protocol_number}"
    return {
        "family_id": family_id,
        "family_label": f"{row.document_type} {row.protocol_number}",
        "family_basis": "official_protocol_number",
        "document_type": slug(row.document_type),
        "official_identifier": row.protocol_number,
        "process_number": process_label,
        "source_system": source_system,
        "version_id": f"{family_id}-v1",
        "version_date": br_date_to_iso(row.document_date),
        "version_date_source": "official_protocol_date",
        "inclusion_date": br_date_to_iso(row.inclusion_date),
        "unit": row.unit,
        "locator": locator,
    }


def br_date_to_iso(value: str) -> str:
    match = re.fullmatch(r"([0-9]{2})/([0-9]{2})/([0-9]{4})", value.strip())
    if not match:
        return value
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slugged = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value.lower()).strip("_")
    return slugged or "documento"


if __name__ == "__main__":
    raise SystemExit(main())
