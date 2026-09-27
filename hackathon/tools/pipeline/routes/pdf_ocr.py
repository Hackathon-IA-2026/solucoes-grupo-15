"""Fourth extraction route (issue #72): OCR/vision for scanned PDFs and for
individually-scanned pages reinserted inside otherwise-native PDFs.

## The two cases this route unifies

1. **Documento inteiro escaneado**: every page's `pdftotext -layout` output
   is near-empty. `pdf_text_generic.py` (#68) and `pdf_llm_spec.py` (#71)
   already detect this — as a *whole-document average* — and return
   `status="pending"` pointing at this issue.
2. **Página individual escaneada dentro de um PDF nativo bom**: e.g. page 24
   of `recurso-48500.000639-2019-07.pdf` — a photographed/scanned page
   reinserted into an otherwise text-layer PDF. The document's *average*
   character density stays well above `MIN_CHARS_PER_PAGE`, so neither #68's
   nor #71's whole-document check ever fires for it. This is the case #71's
   own module docstring ("Remaining, documented differences") already
   flagged as unhandled: page 24's `pdftotext` output is not *empty*, it is
   *degraded* — a sparse, garbled text layer sitting on top of (or baked
   into) a raster scan, e.g. "Ronaldo de Oliveira" comes out as "w ín ald o
   de Oliveira".

Both cases are handled by the *same* per-page loop below — case 1 is simply
what happens when every page independently trips the per-page detector.

## Detection criterion (per page, not per document — acceptance criterion 1)

A page is classified as "sem texto / degradada" when **either** signal fires:

- **Densidade de caracteres**: the page's own
  `pdftotext -layout` output has fewer than `MIN_CHARS_PER_PAGE` (imported
  from `pdf_text_generic.py` — same constant, now applied per page instead
  of as a whole-document average) non-whitespace characters. This is the
  reliable signal for a page with **no** text layer at all.
- **Imagem de página cheia** (`_page_has_full_page_scan_image` below): the
  page embeds at least one raster image (`pdfimages -list`) whose *physical*
  size (pixel dimensions divided by its own resolution, `x-ppi`/`y-ppi`)
  covers at least `MIN_IMAGE_AREA_RATIO` (0.6, i.e. 60%) of the page's own
  area (`pdfinfo -f N -l N`, since — as verified against the real corpus —
  pages within the *same* PDF can have different sizes: page 24 of
  `recurso-48500.000639-2019-07.pdf` is 612×792pt/letter while page 1 of the
  same file is 595×842pt/A4), at a resolution of at least `MIN_IMAGE_PPI`
  (150 ppi — scan-like, not a logo/icon). This is the signal that catches
  case 2: a character-density check alone is *not* reliable there, because
  the page's own sparse/garbled text layer already clears
  `MIN_CHARS_PER_PAGE` (measured on the real page 24: 873 non-whitespace
  characters — `MIN_CHARS_PER_PAGE` is 20). Only a *structural* signal — "is
  most of this page's content actually a raster image, not native text" —
  reliably flags it. Verified against the real PDF (see the issue #72
  evidence pack for the full `pdfimages -list` transcript):
    - page 24: one 2550×3300px JPEG2000 image at 300ppi = 8.5in × 11in =
      exactly the page's own 612×792pt (8.5in × 11in) area → ratio 100%,
      flagged.
    - page 23 (same document, same known "ANEXO" letter — also visibly a
      scan when read): same 2550×3300px @ 300ppi shape → ratio 100%,
      flagged (not required by the acceptance criterion, but a legitimate,
      documented consequence of applying the same structural rule).
    - page 1 (native, not scanned): a 543×223px logo at 577ppi → physical
      size 0.94in × 0.39in against a 595×842pt (8.27in × 11.69in) page →
      ratio 0.4%, correctly not flagged.
    - page 22 (native, has an embedded photo the letter quotes as evidence,
      not a full-page scan): a 560×480px image at 335ppi → 1.67in × 1.43in
      against the same A4 page → ratio 2.5%, correctly not flagged.
  These four measurements are what fixed `MIN_IMAGE_AREA_RATIO`/
  `MIN_IMAGE_PPI` at 0.6/150 — comfortably between the "clearly a full-page
  scan" cases (100%) and the "clearly not" cases (≤2.5%), with margin on
  both sides for other documents in the corpus.

A page tripping *either* signal is routed to OCR/vision (`_ocr_page`,
below); every other page keeps its own `pdftotext -layout` text verbatim,
unmodified by this route.

## OCR mechanism chosen: Bedrock vision, not local `tesseract`

The issue leaves the choice open ("OCR ou modelo com visão") and asks it be
made on quality/cost grounds, piloted on page 24. Both were actually piloted
against the real page 24 (rasterized at 300dpi via `pdftoppm`, see the
evidence pack for the exact commands/outputs):

- **`tesseract` (local, no API cost)**: only the `eng` language pack is
  installed on this machine (`tesseract --list-langs`) — installing
  `tesseract-ocr-por` requires `apt-get`, which needs a `sudo` password not
  available in this environment, so this was not a choice this route could
  make "either way" in practice. Piloted anyway with the `eng` pack: it
  recovers the paragraph structure but garbles every accented word
  (`"evolução"` → `"evolugao"`, `"ção"` → `"c¢f0"`-style artifacts) because
  the English dictionary/model has no notion of Portuguese diacritics, and
  it dropped the "Atenciosamente," + "Ronaldo de Oliveira" signature lines
  entirely (low-contrast region it did not recognize as text at all).
- **Bedrock Converse vision (`us.anthropic.claude-haiku-4-5-20251001-v1:0`,
  same model/region/credentials #71 already validated for the text-spec
  call)**: given the same 300dpi PNG of page 24 with a prompt that
  explicitly forbids summarizing/omitting anything (including boilerplate —
  removal is this route's own filtering step's job, never the vision
  model's), it transcribed the entire page — header stamp, body paragraph
  with correct accents, "Atenciosamente," "Ronaldo de Oliveira" (transcribed
  once as "Rinaldo de Oliveira" — a single-character ambiguity on a proper
  noun the image itself renders faintly; still legible fidelity, and a
  strict improvement over both `pdftotext`'s "w ín ald o de Oliveira" and
  `tesseract`'s outright omission of the line), and the footer address
  block — at ~1.8k input + ~370 output tokens, ≈6-9s and ≈$0.004/page at
  Haiku 4.5 pricing (see `pdf_llm_spec.PRICING_USD_PER_MILLION_TOKENS`,
  reused here).

Bedrock vision wins on the metric the issue asks to decide on (quality per
page, for the actual language of this corpus) at a per-page cost small
enough not to be a practical concern for the corpus's scanned-page count
(see the evidence pack's corpus-wide count). `DEFAULT_MODEL_ID` is therefore
`pdf_llm_spec.DEFAULT_MODEL_ID` (Haiku 4.5) — same default, same override
mechanism (`model_id` constructor argument), for the same reason #71 already
documented (cheapest model that passes the pilot).

## Prompt design (auditable, not just "ask for OCR")

`OCR_PROMPT` below explicitly tells the model to transcribe *everything*,
including boilerplate/footers/logos it might otherwise be tempted to
summarize away, and to mark illegible words rather than guess silently.
This exists to preserve the same "cópia verbatim, nunca paráfrase" guarantee
(D14) the rest of the pipeline relies on: the *only* thing allowed to decide
that a line is boilerplate and remove it is the deterministic filter this
route hands the composed text to afterward
(`pdf_llm_spec.PdfLlmSpecRoute.extract_from_raw_text`) — never the OCR/vision
step itself, silently, by omission. An early pilot without this instruction
had the model quietly drop the page's header stamp and footer address block
on its own initiative; this is exactly the failure mode the explicit
instruction below exists to prevent.

## Composition, not a second `RouteRegistry` entry

Per the established pattern in this codebase (see `pdf_llm_spec.py`'s own
class docstring for how it relates to `pdf_text_generic.py`): `PdfOcrRoute`
is registered *before* `PdfLlmSpecRoute` in `cli.py::build_registry()` and
becomes the actual entry point for every `formato == "pdf"` document.
`PdfOcrRoute.extract()` does its own page-by-page `pdftotext -layout` pass,
classifies each page (see "Detection criterion" above), OCRs/transcribes
only the pages that need it, and then calls
`PdfLlmSpecRoute.extract_from_raw_text(composed_raw_text, page_count,
out_path)` directly — reusing #71's spec-generation/verbatim-filtering logic
byte for byte rather than duplicating it — instead of a second
`RouteRegistry.dispatch` for the same format. `PdfLlmSpecRoute.extract()`
(the whole-document average-density check, and its own two-tier spec cache)
stays exactly as #71 left it, directly callable and independently tested;
it is simply not reached from the registry for real PDFs anymore, the same
relationship `PdfTextGenericRoute` already has with `PdfLlmSpecRoute`.

## Own cache: one OCR'd page, content-addressed

Mirrors #71's own two-tier cache design (see `pdf_llm_spec.py`, "Two-tier
cache"), one level lower — per *page* rather than per document, since the
unit of OCR/vision work here is a page. Keyed by `sha256(rendered PNG
bytes) + PROMPT_VERSION + model_id` (`_ocr_cache_key`), stored under
`<output_dir>/ocr_pages/<key>.json` (a sibling of `llm_specs/`, derived the
same way from `out_path.parent.parent`). Regenerating one page's OCR is:
delete that one file (plus the document's own executor cache entry, so
`extract()` is actually called again) — never touches any other page's or
document's cache entry. Each cache entry also carries `input_tokens`/
`output_tokens`/`cost_usd`/`elapsed_s` — this is where the acceptance
criterion "custo/tempo por página registrado" is satisfied; the corpus-wide
roll-up lives in the evidence pack, computed from these same fields.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from . import ExtractionResult
from .pdf_llm_spec import DEFAULT_MODEL_ID, PdfLlmSpecRoute, estimate_cost_usd
from .pdf_text_generic import MIN_CHARS_PER_PAGE, _extract_raw_text

EXTRACTOR_VERSION = "pdf_ocr@1"
PROMPT_VERSION = "pdf_ocr_prompt@1"

REGION = "us-east-1"
RENDER_DPI = 300

# See module docstring, "Detection criterion" — thresholds fixed against the
# real recurso-48500.000639-2019-07.pdf measurements (pages 1/22 as the
# "clearly not a scan" cases at 0.4%/2.5%, pages 23/24 as the "clearly a
# scan" cases at 100%), never adjusted per document.
MIN_IMAGE_AREA_RATIO = 0.6
MIN_IMAGE_PPI = 150

OCR_PROMPT = """Transcreva TODO o texto visível desta imagem de página de documento oficial, em português, palavra por palavra, incluindo acentuação correta.

Inclua absolutamente tudo que estiver escrito na página, do topo ao rodapé: carimbo/número de processo no topo, cabeçalho, corpo do texto, bloco de assinatura, e rodapé com endereço/telefone/site — mesmo que pareça boilerplate institucional. A decisão de remover boilerplate é feita depois por outra etapa determinística, nunca por você: sua única tarefa é transcrever, nunca resumir, nunca decidir que uma parte "não importa" e por isso pode ser omitida.

Não resuma, não traduza, não corrija erros de digitação do original — copie exatamente o que está escrito, preservando a ordem e as quebras de linha de parágrafos. Se um elemento for puramente gráfico (logotipo sem texto legível), descreva-o entre colchetes, ex.: [logotipo CEMIG]. Se uma palavra estiver ilegível, marque com [ilegível] em vez de adivinhar.

Responda APENAS com o texto transcrito, sem comentários.
"""


@dataclass
class OcrPageResult:
    text: str
    model_id: str
    region: str
    input_tokens: int
    output_tokens: int


class OcrError(Exception):
    """Raised when rendering or the OCR/vision call fails — the caller
    decides the fallback (see `PdfOcrRoute._ocr_page`)."""


class OcrFn(Protocol):
    def __call__(self, image_bytes: bytes) -> OcrPageResult: ...


def make_bedrock_ocr_fn(model_id: str = DEFAULT_MODEL_ID, region: str = REGION) -> OcrFn:
    """Builds an `OcrFn` backed by a real Bedrock `Converse` vision call —
    the production path. Tests inject their own fake `OcrFn` instead (see
    `test_routes_pdf_ocr.py`), same convention as
    `pdf_llm_spec.make_bedrock_generate_fn`."""
    import boto3

    client = boto3.client("bedrock-runtime", region_name=region)

    def ocr(image_bytes: bytes) -> OcrPageResult:
        response = client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"image": {"format": "png", "source": {"bytes": image_bytes}}},
                        {"text": OCR_PROMPT},
                    ],
                }
            ],
            inferenceConfig={"maxTokens": 4096},
        )
        usage = response["usage"]
        text_out = ""
        for block in response["output"]["message"]["content"]:
            if "text" in block:
                text_out += block["text"]
        if not text_out.strip():
            raise OcrError(f"resposta do Bedrock sem texto (stopReason={response.get('stopReason')!r})")
        return OcrPageResult(
            text=text_out,
            model_id=model_id,
            region=region,
            input_tokens=usage["inputTokens"],
            output_tokens=usage["outputTokens"],
        )

    return ocr


def _ocr_cache_key(image_bytes: bytes, model_id: str) -> str:
    digest = hashlib.sha256()
    digest.update(image_bytes)
    digest.update(b"|")
    digest.update(PROMPT_VERSION.encode("utf-8"))
    digest.update(b"|")
    digest.update(model_id.encode("utf-8"))
    return digest.hexdigest()


def _all_pages_raw_text(pdf_path: Path, page_count: int) -> list[str] | None:
    """One whole-document `pdftotext -layout` call, split on the page-
    separator form-feed (`\\x0c`) poppler inserts between pages — instead of
    `page_count` separate `-f N -l N` subprocess spawns (what
    `PdfLlmSpecRoute`/`PdfOcrRoute.extract()` do, following the pattern
    `pdf_text_generic.py` already established). That per-page-subprocess
    pattern is fine for a normal document, but the real corpus has at least
    one outlier — a "Processo" dossier PDF with 3648 pages
    (`022_SEI_0436150_Processo.pdf`, category 03) — where it means 3648
    process spawns for one file. `classify_pdf_pages` (detection-only, used
    by `scan_corpus_report.py` for the corpus-wide count) uses this instead;
    verified byte-for-byte equivalent per page to the `-f N -l N` call
    except for one trailing newline `pdftotext` adds in single-page mode
    (irrelevant to the non-whitespace character count both modes feed into
    `MIN_CHARS_PER_PAGE` — see the evidence pack for the diff). Returns
    `None` (caller falls back to the per-page calls) if the split doesn't
    yield exactly `page_count` chunks — defensive, in case some PDF's
    internal structure doesn't insert a clean form-feed per page."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"], check=True, capture_output=True, text=True
    )
    pages = result.stdout.split("\x0c")
    if len(pages) == page_count + 1 and pages[-1] == "":
        return pages[:-1]
    if len(pages) == page_count:
        return pages
    return None


def _page_size_pts(pdf_path: Path, page: int) -> tuple[float, float]:
    """Parses `pdfinfo -f N -l N`'s own "Page N size: W x H pts (...)" line.
    Called only for pages that `_list_images_by_page` already found at least
    one image on — real corpus documents mix page sizes within one PDF (see
    module docstring), so this cannot be read once for the whole document."""
    result = subprocess.run(
        ["pdfinfo", "-f", str(page), "-l", str(page), str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.strip().startswith("Page") and "size:" in line:
            match = re.search(r"([\d.]+)\s*x\s*([\d.]+)\s*pts", line)
            if match:
                return float(match.group(1)), float(match.group(2))
    raise RuntimeError(f"não foi possível ler o tamanho da página {page} de {pdf_path}")


def _list_images_by_page(pdf_path: Path) -> dict[int, list[tuple[float, float, float, float]]]:
    """One `pdfimages -list` call for the whole document (not one per page —
    poppler already lists every page's images in a single pass). Returns
    `{page_no: [(width_px, height_px, x_ppi, y_ppi), ...]}`, only for rows
    whose `type` column is `image` (excludes `smask`/stencil mask rows,
    which are alpha channels of an already-counted image, not a second
    visible image)."""
    result = subprocess.run(
        ["pdfimages", "-list", str(pdf_path)], check=True, capture_output=True, text=True
    )
    by_page: dict[int, list[tuple[float, float, float, float]]] = {}
    for line in result.stdout.splitlines()[2:]:  # skip the two header lines
        tokens = line.split()
        if len(tokens) < 14:
            continue
        page_no, _num, img_type = tokens[0], tokens[1], tokens[2]
        if img_type != "image":
            continue
        try:
            page_no_int = int(page_no)
            width_px, height_px = float(tokens[3]), float(tokens[4])
            x_ppi, y_ppi = float(tokens[12]), float(tokens[13])
        except ValueError:
            continue
        by_page.setdefault(page_no_int, []).append((width_px, height_px, x_ppi, y_ppi))
    return by_page


def _page_has_full_page_scan_image(
    pdf_path: Path,
    page: int,
    images: list[tuple[float, float, float, float]],
) -> bool:
    if not images:
        return False
    page_w_pts, page_h_pts = _page_size_pts(pdf_path, page)
    page_area_in2 = (page_w_pts / 72.0) * (page_h_pts / 72.0)
    if page_area_in2 <= 0:
        return False
    for width_px, height_px, x_ppi, y_ppi in images:
        if x_ppi <= 0 or y_ppi <= 0:
            continue
        if min(x_ppi, y_ppi) < MIN_IMAGE_PPI:
            continue
        image_area_in2 = (width_px / x_ppi) * (height_px / y_ppi)
        if image_area_in2 / page_area_in2 >= MIN_IMAGE_AREA_RATIO:
            return True
    return False


def _rasterize_page_png(pdf_path: Path, page: int, dpi: int = RENDER_DPI) -> bytes:
    with TemporaryDirectory() as tmp_dir:
        prefix = str(Path(tmp_dir) / "page")
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page), str(pdf_path), prefix],
            check=True,
            capture_output=True,
        )
        produced = sorted(Path(tmp_dir).glob("page-*.png"))
        if not produced:
            raise OcrError(f"pdftoppm não produziu imagem para a página {page}")
        return produced[0].read_bytes()


class PdfOcrRoute:
    """See module docstring for the full design rationale. Registered
    *before* `PdfLlmSpecRoute` in `cli.py::build_registry()` — this is the
    route every `formato == "pdf"` document actually reaches."""

    name = "pdf_ocr"
    extractor_version = EXTRACTOR_VERSION

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        region: str = REGION,
        ocr_fn: OcrFn | None = None,
        ocr_cache_dir: Path | None = None,
        llm_spec_route: PdfLlmSpecRoute | None = None,
    ):
        self.model_id = model_id
        self.region = region
        self._ocr_fn = ocr_fn
        self._ocr_cache_dir_override = ocr_cache_dir
        self._llm_spec_route = llm_spec_route or PdfLlmSpecRoute()

    def can_handle(self, formato: str | None) -> bool:
        return formato == "pdf"

    def extract(self, source_path: Path, out_path: Path) -> ExtractionResult:
        try:
            page_count = _extract_raw_text.count_pages(source_path)
        except Exception as exc:
            return ExtractionResult(
                status="error",
                extractor_version=self.extractor_version,
                route=self.name,
                message=f"pdfinfo falhou: {exc}",
            )

        if page_count == 0:
            return ExtractionResult(
                status="error",
                extractor_version=self.extractor_version,
                route=self.name,
                message="pdfinfo reportou 0 páginas",
            )

        try:
            # One whole-document pdftotext call instead of page_count
            # separate subprocess spawns (see _all_pages_raw_text's
            # docstring) — matters on the real corpus's outlier documents
            # (a 3850-page "Processo" dossier was measured taking minutes
            # under the naive per-page-call version this replaced).
            pages_text = _all_pages_raw_text(source_path, page_count)
            if pages_text is None:
                pages_text = [
                    _extract_raw_text.extract_page(source_path, p) for p in range(1, page_count + 1)
                ]
            images_by_page = _list_images_by_page(source_path)
        except Exception as exc:
            return ExtractionResult(
                status="error",
                extractor_version=self.extractor_version,
                route=self.name,
                message=f"falha ao inspecionar o PDF: {exc}",
            )

        degraded_pages: list[int] = []
        for page in range(1, page_count + 1):
            char_count = len(re.sub(r"\s", "", pages_text[page - 1]))
            is_degraded = char_count < MIN_CHARS_PER_PAGE
            if not is_degraded:
                try:
                    is_degraded = _page_has_full_page_scan_image(
                        source_path, page, images_by_page.get(page, [])
                    )
                except Exception:
                    # Structural check failing (e.g. pdfinfo hiccup on one
                    # page) is not itself grounds to error the whole
                    # document out — fall through on char density alone for
                    # that page, same conservative posture as the LLM-spec
                    # fallback in pdf_llm_spec.py.
                    pass
            if is_degraded:
                degraded_pages.append(page)

        ocr_notes: list[str] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost_usd = 0.0
        cost_known = True

        raw_lines: list[str] = []
        for page in range(1, page_count + 1):
            raw_lines.append(f"<!-- pdftotext:page {page} -->")
            if page in degraded_pages:
                ocr_text, ocr_message, usage = self._ocr_page(source_path, page, out_path)
                raw_lines.extend(ocr_text.split("\n"))
                if usage is not None:
                    total_input_tokens += usage.input_tokens
                    total_output_tokens += usage.output_tokens
                    cost = estimate_cost_usd(usage.model_id, usage.input_tokens, usage.output_tokens)
                    if cost is None:
                        cost_known = False
                    else:
                        total_cost_usd += cost
                if ocr_message:
                    ocr_notes.append(f"p.{page}: {ocr_message}")
            else:
                raw_lines.extend(pages_text[page - 1].split("\n"))
        raw_text = "\n".join(raw_lines)

        result = self._llm_spec_route.extract_from_raw_text(raw_text, page_count, out_path)
        # extract_from_raw_text() is a method on the delegate PdfLlmSpecRoute
        # instance, so its ExtractionResult carries *that* route's own
        # name/extractor_version — overwrite with this route's own identity
        # before returning, since this is the route the executor's cache
        # actually keys on (see module docstring, "Composition, not a
        # second RouteRegistry entry").
        result.route = self.name
        result.extractor_version = self.extractor_version

        if degraded_pages:
            summary = (
                f"{len(degraded_pages)}/{page_count} página(s) via OCR/visão "
                f"({self.model_id}, páginas {degraded_pages}); "
                f"{total_input_tokens}+{total_output_tokens} tokens"
                + (f", ~US${total_cost_usd:.4f}" if cost_known else "")
            )
            pieces = [summary] + ocr_notes
            if result.message:
                pieces.append(result.message)
            result.message = "; ".join(pieces)

        return result

    def _ocr_page(
        self, source_path: Path, page: int, out_path: Path
    ) -> tuple[str, str | None, OcrPageResult | None]:
        """Returns `(text_for_this_page, note_for_message, usage_or_None)`.
        On any failure (rendering or the OCR/vision call itself), falls back
        to this page's own `pdftotext -layout` text rather than erroring the
        whole document out — same documented precedence pattern
        `pdf_llm_spec.py` uses for a failed/invalid LLM call."""
        try:
            image_bytes = _rasterize_page_png(source_path, page)
        except Exception as exc:
            fallback = _extract_raw_text.extract_page(source_path, page)
            return fallback, f"pdftoppm falhou, mantido texto nativo degradado: {exc}", None

        cache_dir = self._ocr_cache_dir(out_path)
        cache_key = _ocr_cache_key(image_bytes, self.model_id)
        cache_path = cache_dir / f"{cache_key}.json"

        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            usage = OcrPageResult(
                text=cached["text"],
                model_id=cached["model_id"],
                region=cached["region"],
                input_tokens=cached["input_tokens"],
                output_tokens=cached["output_tokens"],
            )
            return cached["text"], "OCR/visão em cache", usage

        ocr_fn = self._ocr_fn or make_bedrock_ocr_fn(self.model_id, self.region)
        t0 = time.monotonic()
        try:
            result = ocr_fn(image_bytes)
        except Exception as exc:
            fallback = _extract_raw_text.extract_page(source_path, page)
            return fallback, f"OCR/visão falhou, mantido texto nativo degradado: {exc}", None
        elapsed_s = time.monotonic() - t0

        cost_usd = estimate_cost_usd(result.model_id, result.input_tokens, result.output_tokens)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "text": result.text,
                    "model_id": result.model_id,
                    "region": result.region,
                    "prompt_version": PROMPT_VERSION,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cost_usd": cost_usd,
                    "elapsed_s": round(elapsed_s, 2),
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return result.text, None, result

    def _ocr_cache_dir(self, out_path: Path) -> Path:
        if self._ocr_cache_dir_override is not None:
            return self._ocr_cache_dir_override
        # Same derivation `pdf_llm_spec.py._spec_cache_dir` uses: `out_path`
        # is `<output_dir>/markdown/<sha256>__<extractor_version>.md`, a
        # route never gets `output_dir` directly (extraction-route
        # contract) — this derives the sibling `ocr_pages/` directory.
        return out_path.parent.parent / "ocr_pages"


def classify_pdf_pages(pdf_path: Path) -> tuple[int, list[int]]:
    """Standalone detection-only helper (no OCR call, no cost) — used by
    `scan_corpus_report.py` for the corpus-wide scanned-page count
    (acceptance criterion), and reused here so the count is computed with
    the *exact* same criterion `PdfOcrRoute.extract()` applies, never a
    second, drifting copy of it. Returns `(page_count, degraded_page_numbers)`.

    Uses `_all_pages_raw_text`'s single whole-document `pdftotext` call
    (falling back to one call per page only if that doesn't cleanly split
    into `page_count` chunks) — see that function's docstring for why this
    matters on the real corpus."""
    page_count = _extract_raw_text.count_pages(pdf_path)
    images_by_page = _list_images_by_page(pdf_path)
    pages_text = _all_pages_raw_text(pdf_path, page_count)
    if pages_text is None:
        pages_text = [_extract_raw_text.extract_page(pdf_path, p) for p in range(1, page_count + 1)]
    degraded: list[int] = []
    for page in range(1, page_count + 1):
        char_count = len(re.sub(r"\s", "", pages_text[page - 1]))
        is_degraded = char_count < MIN_CHARS_PER_PAGE
        if not is_degraded:
            is_degraded = _page_has_full_page_scan_image(pdf_path, page, images_by_page.get(page, []))
        if is_degraded:
            degraded.append(page)
    return page_count, degraded
