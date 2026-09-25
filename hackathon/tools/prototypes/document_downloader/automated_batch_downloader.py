"""PROTOTYPE: automate SEI batch collection after a human solves CAPTCHA.

The command opens a visible browser, fills public SEI filters, and waits while
the person solves CAPTCHA and clicks Pesquisar. After that, it collects the
first N process families and downloads every public document through the same
browser session. CAPTCHA is never solved or bypassed by this program.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

from assisted_process_downloader import search_url
from discover_official_page import LinkTextParser, br_date_to_iso, resolve_path, slug
from download_families import (
    SourceDocument,
    download_all,
    group_by_family,
    print_plan,
    print_state,
    print_summary,
    write_outputs,
)


PROCESS_RE = re.compile(r"[0-9]{5}\.[0-9]{6}/[0-9]{4}-[0-9]{2}")

JS_PARSE_PROCESS = r"""
(html) => {
  const documentPage = new DOMParser().parseFromString(html, 'text/html');
  const header = {};
  documentPage.querySelectorAll('#tblCabecalho tr').forEach((row) => {
    if (row.cells.length >= 2) {
      header[row.cells[0].textContent.replace(':', '').trim()] =
        row.cells[1].textContent.replace(/\s+/g, ' ').trim();
    }
  });
  const rows = [];
  const table = documentPage.querySelector('#tblDocumentos');
  if (table) {
    [...table.rows].forEach((row) => {
      if (row.querySelector('th') || row.cells.length < 6) return;
      const anchor = row.cells[1].querySelector('a');
      const onclick = anchor ? (anchor.getAttribute('onclick') || '') : '';
      const openMatch = onclick.match(/window\.open\('([^']+)'/);
      const href = openMatch ? openMatch[1] :
        (anchor && anchor.getAttribute('href') && !anchor.getAttribute('href').startsWith('javascript')
          ? anchor.getAttribute('href') : '');
      const unitAnchor = row.cells[5].querySelector('a');
      rows.push({
        sei: row.cells[1].textContent.trim(),
        type: row.cells[2].textContent.replace(/\s+/g, ' ').trim(),
        date: row.cells[3].textContent.trim(),
        inclusionDate: row.cells[4].textContent.trim(),
        unit: unitAnchor ? unitAnchor.textContent.trim() : row.cells[5].textContent.trim(),
        href: href ? new URL(href, 'https://sei.aneel.gov.br/sei/modulos/pesquisa/').href : '',
        relatedProcess: href.includes('md_pesq_processo_exibir'),
      });
    });
  }
  return { header, rows, valid: Boolean(table) };
}
"""

JS_FETCH_B64 = r"""
async (url) => {
  const response = await fetch(url, { credentials: 'include' });
  const bytes = new Uint8Array(await response.arrayBuffer());
  let binary = '';
  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode.apply(null, bytes.subarray(index, index + 0x8000));
  }
  return {
    status: response.status,
    body: btoa(binary),
  };
}
"""


@dataclass(frozen=True)
class ProcessHit:
    process_number: str
    href: str | None = None


def main() -> int:
    args = parse_args()
    output_root = resolve_path(args.out)
    output_root.mkdir(parents=True, exist_ok=True)
    profile_dir = resolve_path(args.profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    sync_playwright = load_playwright()
    with sync_playwright() as playwright:
        context = launch_context(playwright, args, profile_dir)
        try:
            search_page = context.new_page()
            search_page.goto(search_url(args.source_system), wait_until="domcontentloaded")
            print("Aguardando o formulario do SEI ficar disponivel.")
            print("Se o navegador mostrar verificacao da Cloudflare, conclua apenas ela.")
            search_page.wait_for_selector(
                "#txtDataInicio",
                state="visible",
                timeout=args.wait_timeout_seconds * 1000,
            )
            fill_sei_search(search_page, args)
            print("Filtros preenchidos no navegador.")

            if args.stop_after_prefill:
                print("Parada solicitada apos o pre-preenchimento.")
                return 0

            print("Conclua o CAPTCHA e clique em Pesquisar no navegador aberto.")
            print("O baixador continua automaticamente quando o SEI mostrar resultados.")
            hits = wait_for_search_results(search_page, args.wait_timeout_seconds)
            selected_hits = select_hits(hits, args.limit_families)
            if not selected_hits:
                raise SystemExit("O SEI nao retornou processos para esse filtro.")

            save_source_page(output_root / "source-pages" / "resultados.html", search_page.content())
            print(f"processos encontrados: {len(hits)}")
            print(f"familias selecionadas: {len(selected_hits)}")
            for index, hit in enumerate(selected_hits, start=1):
                print(f"{index}. {hit.process_number}")

            manifests = collect_process_manifests(context, selected_hits, args, output_root)
            combined = combine_manifests(manifests, args)
            source_manifest = output_root / "source_manifest.json"
            source_manifest.write_text(
                json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            documents = [SourceDocument.from_dict(item) for item in combined["documents"]]
            families = group_by_family(documents)
            print_state("carregados", documents)
            print_state("selecionados", documents)
            print(f"familias selecionadas: {len(families)}")
            print_plan(families)

            if args.dry_run:
                print(f"manifesto fonte: {source_manifest}")
                return 0

            downloader = BrowserSessionDownloader(context, search_page)
            results = download_all(families, output_root, download_url_fn=downloader.download)
            write_outputs(results, output_root)
            print_summary(results, output_root)
            print(f"manifesto fonte: {source_manifest}")
            ok_statuses = {"downloaded", "metadata_only"}
            return 0 if all(item["status"] in ok_statuses for item in results) else 2
        except Exception as exc:
            if "closed" in str(exc).lower():
                raise SystemExit(
                    "A janela do navegador foi fechada. Rode novamente e deixe-a aberta "
                    "ate o fim da coleta."
                ) from exc
            raise
        finally:
            context.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automate SEI batch collection after a human solves CAPTCHA."
    )
    parser.add_argument("--source-system", default="sei", choices=["sei"])
    parser.add_argument("--theme", required=True, help="Theme/filter for the official search.")
    parser.add_argument(
        "--theme-field",
        default="tipo-processo",
        choices=["tipo-processo", "texto-livre"],
        help="Official SEI field that receives --theme.",
    )
    parser.add_argument("--date-from", required=True, help="Search start date (DD/MM/YYYY).")
    parser.add_argument("--date-to", required=True, help="Search end date (DD/MM/YYYY).")
    parser.add_argument("--limit-families", type=int, default=3)
    parser.add_argument("--out", required=True, help="Output directory for public files and metadata.")
    parser.add_argument(
        "--browser-channel",
        default="auto",
        help="Browser channel: auto, msedge, chrome or chromium (default: auto).",
    )
    parser.add_argument("--wait-timeout-seconds", type=int, default=600)
    parser.add_argument(
        "--profile-dir",
        default="hackathon/.prototype-downloads/sei-browser-profile",
        help="Persistent browser profile used to retain the verified public session.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Collect and print plan only.")
    parser.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--stop-after-prefill", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def launch_context(playwright: Any, args: argparse.Namespace, profile_dir: Path) -> Any:
    channels = ("msedge", "chrome", None) if args.browser_channel == "auto" else (args.browser_channel,)
    errors = []
    for channel in channels:
        options: dict[str, Any] = {
            "user_data_dir": str(profile_dir),
            "headless": args.headless,
            "accept_downloads": True,
            "locale": "pt-BR",
        }
        if channel and channel != "chromium":
            options["channel"] = channel
        try:
            context = playwright.chromium.launch_persistent_context(**options)
            print(f"Navegador aberto ({channel or 'chromium do Playwright'}).")
            return context
        except Exception as exc:
            errors.append(str(exc))
    raise SystemExit(
        "Nao foi possivel abrir Edge, Chrome ou Chromium. Instale o navegador do "
        "Playwright com: python -m playwright install chromium\n" + errors[-1]
    )


def search_field_values(
    theme: str, theme_field: str, date_from: str, date_to: str
) -> dict[str, str | None]:
    return {
        "select_label": theme if theme_field == "tipo-processo" else None,
        "free_text": theme if theme_field == "texto-livre" else None,
        "date_from": date_from,
        "date_to": date_to,
    }


def fill_sei_search(page: Any, args: argparse.Namespace) -> None:
    values = search_field_values(args.theme, args.theme_field, args.date_from, args.date_to)
    page.locator("#chkSinProcessos").check()
    if values["select_label"]:
        page.locator("#selTipoProcedimentoPesquisa").select_option(
            label=values["select_label"]
        )
    if values["free_text"]:
        page.locator("#q").fill(values["free_text"])
    page.locator("#txtDataInicio").fill(values["date_from"])
    page.locator("#txtDataFim").fill(values["date_to"])
    page.locator("#txtInfraCaptcha").focus()


def wait_for_search_results(page: Any, timeout_seconds: int) -> list[ProcessHit]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        hits = extract_process_hits(page.content(), page.url)
        if hits:
            return hits
        page.wait_for_timeout(1000)
    raise SystemExit(
        "Tempo esgotado aguardando resultados do SEI. Conclua o CAPTCHA e clique "
        "em Pesquisar enquanto a janela estiver aberta."
    )


def extract_process_hits(raw: str, source_url: str) -> list[ProcessHit]:
    parser = LinkTextParser()
    parser.feed(raw)
    text = parser.text() if parser.text_parts else raw
    links = parser.links if parser.text_parts else {}
    text = html.unescape(text).replace("\xa0", " ")
    hits_by_process: dict[str, ProcessHit] = {}

    for process_number in PROCESS_RE.findall(text):
        href = links.get(process_number)
        hits_by_process.setdefault(
            process_number,
            ProcessHit(process_number, urljoin(source_url, href) if href else None),
        )
    for label, href in links.items():
        for process_number in PROCESS_RE.findall(label):
            hits_by_process.setdefault(
                process_number,
                ProcessHit(process_number, urljoin(source_url, href)),
            )
    return list(hits_by_process.values())


def select_hits(hits: list[ProcessHit], limit_families: int) -> list[ProcessHit]:
    return hits[:limit_families]


def collect_process_manifests(
    context: Any,
    hits: list[ProcessHit],
    args: argparse.Namespace,
    output_root: Path,
) -> list[dict[str, Any]]:
    manifests = []
    for hit in hits:
        if not hit.href:
            raise SystemExit(
                "O resultado do SEI nao expos um link navegavel para "
                f"{hit.process_number}. Esta familia nao pode ser coletada automaticamente."
            )
        page = context.new_page()
        try:
            page.goto(hit.href, wait_until="domcontentloaded", timeout=90_000)
            raw = page.content()
            save_source_page(
                output_root / "source-pages" / f"{slug(hit.process_number)}.html",
                raw,
            )
            info = page.evaluate(JS_PARSE_PROCESS, raw)
            if not info["valid"]:
                raise SystemExit(
                    f"A pagina publica de {hit.process_number} nao apresentou a arvore de "
                    "documentos. Ela pode estar indisponivel ou bloqueada."
                )
            manifests.append(process_manifest(info, hit, args.source_system))
        finally:
            page.close()
    return manifests


def process_manifest(info: dict[str, Any], hit: ProcessHit, source_system: str) -> dict[str, Any]:
    process_number = info["header"].get("Processo", hit.process_number)
    process_slug = slug(process_number).replace("_", "-")
    family_id = f"{source_system}-process-{process_slug}"
    documents = []
    for row in info["rows"]:
        locator = (
            f"metadata://{source_system}/related-process/{row['sei']}"
            if row["relatedProcess"]
            else row["href"] or f"missing://{source_system}/{row['sei']}"
        )
        documents.append(
            {
                "family_id": family_id,
                "family_label": f"Processo {process_number}",
                "family_basis": "official_process_number",
                "document_type": slug(row["type"]),
                "official_identifier": row["sei"],
                "process_number": process_number,
                "source_system": source_system,
                "version_id": f"{family_id}-{row['sei']}",
                "version_date": br_date_to_iso(row["date"]),
                "version_date_source": "official_protocol_date",
                "inclusion_date": br_date_to_iso(row["inclusionDate"]),
                "unit": row["unit"],
                "locator": locator,
            }
        )
    return {
        "process_number": process_number,
        "process_type": info["header"].get("Tipo", ""),
        "documents": documents,
    }


def combine_manifests(manifests: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    documents = []
    processes = []
    for manifest in manifests:
        processes.append(manifest["process_number"])
        documents.extend(manifest["documents"])
    return {
        "schema_version": "prototype-document-downloader-v1",
        "generated_from": "automated_batch_after_human_captcha",
        "source_system": args.source_system,
        "family_mode": "process",
        "theme": args.theme,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "limit_families": args.limit_families,
        "processes": processes,
        "documents": documents,
    }


class BrowserSessionDownloader:
    """Download public documents, falling back to fetch inside the verified browser."""

    def __init__(self, context: Any, page: Any) -> None:
        self._request = context.request
        self._page = page
        self._use_browser_fetch = False

    def download(self, url: str, target_path: Path) -> None:
        status, body = self._get(url)
        if status != 200 or not body:
            raise OSError(f"public source returned HTTP {status}: {url}")
        target_path.write_bytes(body)

    def _get(self, url: str) -> tuple[int, bytes]:
        if not self._use_browser_fetch:
            response = self._request.get(url, timeout=180_000)
            body = response.body()
            content_type = response.headers.get("content-type", "")
            if not self._is_blocked(response.status, content_type, body):
                return response.status, body
            print("Requisicao direta bloqueada; continuando pela sessao do navegador.")
            self._use_browser_fetch = True
        response = self._page.evaluate(JS_FETCH_B64, url)
        return response["status"], base64.b64decode(response["body"])

    @staticmethod
    def _is_blocked(status: int, content_type: str, body: bytes) -> bool:
        if status in {403, 429, 503}:
            return True
        snippet = body[:5000]
        return "text/html" in content_type and (
            b"challenge-platform" in snippet or b"Just a moment" in snippet
        )


def save_source_page(path: Path, raw: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw, encoding="utf-8")


def load_playwright() -> Callable[..., Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright nao esta instalado. Execute: python -m pip install -r "
            "hackathon/tools/prototypes/document_downloader/requirements.txt"
        ) from exc
    return sync_playwright


if __name__ == "__main__":
    raise SystemExit(main())
