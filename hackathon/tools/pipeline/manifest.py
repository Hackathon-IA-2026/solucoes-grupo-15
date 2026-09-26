"""Corpus manifest: one record per document across the whole `hackathon/data`
corpus (issue #68 — prefactor for the batch extraction pipeline).

This module only *catalogs* documents. It never extracts text and never
decides which extraction route handles a document — that is `routes/` and
`executor.py`. Its two jobs are:

1. Walk both corpora under `hackathon/data/` and produce one
   :class:`ManifestDocument` per document:

   - ``processos aneel/processos/<categoria>/<processo>/`` — built from each
     category's ``_indice_*.csv`` (one row per document; source of truth for
     path/type/date/status) and, for the small amount of data the CSV does
     not carry, each process's ``_processo.json`` (used here only to fill
     ``processo_url``, the SEI consultation link — never as a second, looser
     source of the fields the CSV already gives us, to keep one document one
     record).
   - ``case-1-carolina-mmgd/<processo>/`` — the 10 hand-curated PDFs from
     issue #59. This corpus has no `_indice_*.csv`/`_processo.json`: the
     `tipo_documento` and `processo` are derived from the filename
     convention documented in `case-1-carolina-mmgd/README.md`
     (`<tipo>-<processo-com-hifen>.pdf`). The `.md` siblings already sitting
     next to these PDFs are issue #59's hand-verified output, not corpus
     *input* — the manifest walk skips them on purpose (see
     `is_case1_manual_markdown`).

2. Compute ``corpus_version``: a deterministic hash of the manifest's
   document-identity fields (never of triage decisions or of anything that
   can change without the underlying files changing, like the SEI portal's
   rotating query-string tokens in `processo_url`). Same corpus contents ->
   same hash, by construction (`compute_corpus_version`).

ZIP handling (M1/I7's "ZIPs are expanded, origin recorded"): a `.zip` listed
by a CSV row is never itself an extraction candidate — it is expanded and
each member becomes its own :class:`ManifestDocument`, carrying `origem`
(the zip's own manifest path plus the member name inside it) so provenance
survives the expansion. Zips nested inside zips are expanded recursively
(seen in the real corpus — issue #68 exploration), bounded by
`MAX_ZIP_DEPTH` as a zip-bomb guard.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

CASE1_CORPUS_ID = "case-1-carolina-mmgd"
ANEEL_CORPUS_ID = "processos-aneel"

MAX_ZIP_DEPTH = 5

# Filename convention documented in hackathon/data/case-1-carolina-mmgd/README.md:
# "<tipo-slug>-<processo-com-hifen>.pdf". Longest prefixes first so
# "complementacao-recurso" doesn't get shadowed by a future "recurso" match.
_CASE1_TIPO_BY_PREFIX = (
    ("complementacao-recurso-", "Complementação de Recurso"),
    ("auto-infracao-", "Auto de Infração"),
    ("recurso-", "Recurso"),
    ("voto-", "Voto"),
)


@dataclass
class ManifestDocument:
    """One document, from either corpus, ready for triage/extraction dispatch."""

    corpus_id: str
    categoria: str | None
    processo: str
    numero_sei: str | None
    tipo_documento: str
    data: str | None
    caminho: str | None  # POSIX path relative to REPO_ROOT; None when status_origem == "restrito"
    formato: str | None  # lowercase extension without the dot; None when caminho is None
    bytes: int | None
    sha256: str | None
    status_origem: str  # "ok" | "restrito"
    origem: dict | None = None  # zip lineage, or None for a document that was never zipped
    processo_url: str | None = None
    descartado: bool = False
    motivo_descarte: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> ManifestDocument:
        return ManifestDocument(**data)

    def identity_key(self) -> tuple:
        """Fields that define *what document this is* — see module docstring
        for why this excludes triage flags and `processo_url`."""
        origem_key = None
        if self.origem is not None:
            origem_key = tuple(sorted(self.origem.items()))
        return (
            self.corpus_id,
            self.categoria,
            self.processo,
            self.numero_sei,
            self.tipo_documento,
            self.data,
            self.caminho,
            self.formato,
            self.sha256,
        ) + (origem_key,)


class Sha256Cache:
    """Persists ``sha256(path)`` keyed by ``(path, size, mtime_ns)`` so that
    rebuilding the manifest across runs does not re-hash the ~3.3 GB corpus
    every time — only files that actually changed on disk get re-hashed.
    Pure speed optimization for manifest building; unrelated to the
    extraction cache in `executor.py`, which is keyed by
    ``(sha256, extractor_version)``."""

    def __init__(self, cache_path: Path | None):
        self._cache_path = cache_path
        self._entries: dict[str, dict] = {}
        if cache_path is not None and cache_path.exists():
            self._entries = json.loads(cache_path.read_text(encoding="utf-8"))

    def get_or_compute(self, path: Path) -> str:
        stat = path.stat()
        key = str(path)
        cached = self._entries.get(key)
        if cached and cached["size"] == stat.st_size and cached["mtime_ns"] == stat.st_mtime_ns:
            return cached["sha256"]
        digest = sha256_file(path)
        self._entries[key] = {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": digest,
        }
        return digest

    def save(self) -> None:
        if self._cache_path is None:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(json.dumps(self._entries), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extension_of(name: str) -> str | None:
    if "." not in name.rsplit("/", 1)[-1]:
        return None
    return name.rsplit(".", 1)[-1].lower()


def build_corpus_manifest(
    data_root: Path,
    sha_cache: Sha256Cache | None = None,
    base_dir: Path = REPO_ROOT,
) -> list[ManifestDocument]:
    """Walk `data_root` (normally `hackathon/data`) and return every document
    in both corpora, ZIPs already expanded into their members.

    `base_dir` is what `caminho` is made relative to — always `REPO_ROOT` in
    production; tests pass their own `tmp_path` so a synthetic corpus never
    needs to live under the real repo root.
    """
    documents: list[ManifestDocument] = []
    case1_dir = data_root / "case-1-carolina-mmgd"
    if case1_dir.is_dir():
        documents.extend(_scan_case1(case1_dir, base_dir))

    aneel_processos_dir = data_root / "processos aneel" / "processos"
    if aneel_processos_dir.is_dir():
        for categoria_dir in sorted(p for p in aneel_processos_dir.iterdir() if p.is_dir()):
            documents.extend(_scan_aneel_categoria(categoria_dir, sha_cache, base_dir))

    return documents


def is_case1_manual_markdown(path: Path) -> bool:
    """True for the `.md` files issue #59 hand-wrote next to their source
    PDFs in `case-1-carolina-mmgd/` — prior curated *output*, not corpus
    input, so the manifest walk must not pick them up as documents."""
    return path.suffix.lower() == ".md"


def _scan_case1(case1_dir: Path, base_dir: Path) -> Iterator[ManifestDocument]:
    for processo_dir in sorted(p for p in case1_dir.iterdir() if p.is_dir()):
        processo = _dirname_to_processo(processo_dir.name)
        for file_path in sorted(processo_dir.iterdir()):
            if not file_path.is_file() or is_case1_manual_markdown(file_path):
                continue
            tipo_documento = _case1_tipo_documento(file_path.name)
            digest = sha256_file(file_path)
            yield ManifestDocument(
                corpus_id=CASE1_CORPUS_ID,
                categoria=None,
                processo=processo,
                numero_sei=None,
                tipo_documento=tipo_documento,
                data=None,
                caminho=_relative_posix(file_path, base_dir),
                formato=_extension_of(file_path.name),
                bytes=file_path.stat().st_size,
                sha256=digest,
                status_origem="ok",
            )


def _case1_tipo_documento(filename: str) -> str:
    lowered = filename.lower()
    for prefix, tipo in _CASE1_TIPO_BY_PREFIX:
        if lowered.startswith(prefix):
            return tipo
    return "Desconhecido"


def _dirname_to_processo(dirname: str) -> str:
    """`48500.004024-2017-80` (case-1 folder) or `48500.027248_2026-51`
    (processos aneel folder) -> `48500.004024/2017-80` (SEI display form)."""
    normalized = dirname.replace("_", "-")
    parts = normalized.split("-")
    if len(parts) == 3:
        prefix, year, seq = parts
        return f"{prefix}/{year}-{seq}"
    return normalized


def _scan_aneel_categoria(
    categoria_dir: Path, sha_cache: Sha256Cache | None, base_dir: Path
) -> Iterator[ManifestDocument]:
    categoria = categoria_dir.name
    csv_paths = sorted(categoria_dir.glob("_indice_*.csv"))
    processo_urls = _load_processo_urls(categoria_dir)

    for csv_path in csv_paths:
        for row in _read_indice_csv(csv_path):
            processo_dirname = row["processo"].replace("/", "_")
            processo_dir = categoria_dir / processo_dirname
            arquivo = row["arquivo"].strip()
            status = row["status"].strip()
            processo_url = processo_urls.get(row["processo"])

            if not arquivo:
                # "restrito": ANEEL did not make the file available for
                # download. No path, no hash, no format — this is a
                # pending document, not a discard (see triage.py) and not a
                # silent gap (see executor.py's report).
                yield ManifestDocument(
                    corpus_id=ANEEL_CORPUS_ID,
                    categoria=categoria,
                    processo=row["processo"],
                    numero_sei=row["sei"] or None,
                    tipo_documento=row["tipo_documento"],
                    data=row["data"] or None,
                    caminho=None,
                    formato=None,
                    bytes=None,
                    sha256=None,
                    status_origem=status or "restrito",
                    processo_url=processo_url,
                )
                continue

            file_path = processo_dir / arquivo
            if not file_path.is_file():
                # Indexed but missing on disk (partial local checkout) —
                # still recorded, still not a silent gap.
                yield ManifestDocument(
                    corpus_id=ANEEL_CORPUS_ID,
                    categoria=categoria,
                    processo=row["processo"],
                    numero_sei=row["sei"] or None,
                    tipo_documento=row["tipo_documento"],
                    data=row["data"] or None,
                    caminho=None,
                    formato=_extension_of(arquivo),
                    bytes=None,
                    sha256=None,
                    status_origem="ausente_no_disco",
                    processo_url=processo_url,
                )
                continue

            formato = _extension_of(arquivo)
            if formato == "zip":
                # The zip container itself is never a manifest document —
                # only its expanded members are (issue #68: "ZIPs são
                # descompactados e seus arquivos entram no manifesto como
                # documentos próprios, com a origem registrada").
                yield from _expand_zip(
                    zip_path=file_path,
                    corpus_id=ANEEL_CORPUS_ID,
                    categoria=categoria,
                    processo=row["processo"],
                    numero_sei=row["sei"] or None,
                    tipo_documento=row["tipo_documento"],
                    data=row["data"] or None,
                    processo_url=processo_url,
                    zip_lineage=[_relative_posix(file_path, base_dir)],
                )
                continue

            digest = _cached_or_computed(sha_cache, file_path)
            yield ManifestDocument(
                corpus_id=ANEEL_CORPUS_ID,
                categoria=categoria,
                processo=row["processo"],
                numero_sei=row["sei"] or None,
                tipo_documento=row["tipo_documento"],
                data=row["data"] or None,
                caminho=_relative_posix(file_path, base_dir),
                formato=formato,
                bytes=file_path.stat().st_size,
                sha256=digest,
                status_origem=status,
                processo_url=processo_url,
            )


def _cached_or_computed(sha_cache: Sha256Cache | None, path: Path) -> str:
    if sha_cache is not None:
        return sha_cache.get_or_compute(path)
    return sha256_file(path)


def _expand_zip(
    zip_path: Path,
    corpus_id: str,
    categoria: str | None,
    processo: str,
    numero_sei: str | None,
    tipo_documento: str,
    data: str | None,
    processo_url: str | None,
    zip_lineage: list[str],
    depth: int = 0,
) -> Iterator[ManifestDocument]:
    if depth >= MAX_ZIP_DEPTH:
        return
    try:
        zf = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError):
        return
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            member_bytes = zf.read(info)
            member_formato = _extension_of(info.filename)
            member_sha256 = sha256_bytes(member_bytes)
            origem = {
                "zip_caminho": zip_lineage[0],
                "zip_membro": info.filename,
                "profundidade": depth + 1,
            }
            if len(zip_lineage) > 1:
                origem["zip_lineage"] = list(zip_lineage)

            if member_formato == "zip":
                # Nested zip: recurse into an in-memory copy instead of
                # writing a temp file — members stay attributed to the
                # outermost zip's manifest path via `zip_lineage`.
                import io

                nested_lineage = zip_lineage + [info.filename]
                with zipfile.ZipFile(io.BytesIO(member_bytes)) as nested_zf:
                    for nested_info in nested_zf.infolist():
                        if nested_info.is_dir():
                            continue
                        yield from _expand_zip_entry(
                            nested_zf,
                            nested_info,
                            corpus_id=corpus_id,
                            categoria=categoria,
                            processo=processo,
                            numero_sei=numero_sei,
                            tipo_documento=tipo_documento,
                            data=data,
                            processo_url=processo_url,
                            zip_lineage=nested_lineage,
                            depth=depth + 1,
                        )
                continue

            yield ManifestDocument(
                corpus_id=corpus_id,
                categoria=categoria,
                processo=processo,
                numero_sei=numero_sei,
                tipo_documento=tipo_documento,
                data=data,
                caminho=None,
                formato=member_formato,
                bytes=info.file_size,
                sha256=member_sha256,
                status_origem="ok",
                origem=origem,
                processo_url=processo_url,
            )


def _expand_zip_entry(
    zf: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    corpus_id: str,
    categoria: str | None,
    processo: str,
    numero_sei: str | None,
    tipo_documento: str,
    data: str | None,
    processo_url: str | None,
    zip_lineage: list[str],
    depth: int,
) -> Iterator[ManifestDocument]:
    """Handle one already-opened nested-zip member (depth >= 1)."""
    if depth >= MAX_ZIP_DEPTH:
        return
    member_bytes = zf.read(info)
    member_formato = _extension_of(info.filename)
    if member_formato == "zip":
        import io

        nested_lineage = zip_lineage + [info.filename]
        with zipfile.ZipFile(io.BytesIO(member_bytes)) as nested_zf:
            for nested_info in nested_zf.infolist():
                if nested_info.is_dir():
                    continue
                yield from _expand_zip_entry(
                    nested_zf,
                    nested_info,
                    corpus_id=corpus_id,
                    categoria=categoria,
                    processo=processo,
                    numero_sei=numero_sei,
                    tipo_documento=tipo_documento,
                    data=data,
                    processo_url=processo_url,
                    zip_lineage=nested_lineage,
                    depth=depth + 1,
                )
        return

    origem = {
        "zip_caminho": zip_lineage[0],
        "zip_membro": info.filename,
        "profundidade": depth + 1,
        "zip_lineage": list(zip_lineage),
    }
    yield ManifestDocument(
        corpus_id=corpus_id,
        categoria=categoria,
        processo=processo,
        numero_sei=numero_sei,
        tipo_documento=tipo_documento,
        data=data,
        caminho=None,
        formato=member_formato,
        bytes=info.file_size,
        sha256=sha256_bytes(member_bytes),
        status_origem="ok",
        origem=origem,
        processo_url=processo_url,
    )


def _read_indice_csv(csv_path: Path) -> Iterator[dict]:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";", quotechar='"')
        yield from reader


def _load_processo_urls(categoria_dir: Path) -> dict[str, str]:
    urls: dict[str, str] = {}
    for processo_json_path in categoria_dir.glob("*/_processo.json"):
        try:
            data = json.loads(processo_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        processo = data.get("processo")
        url = data.get("url")
        if processo and url:
            urls[processo] = url
    return urls


def _relative_posix(path: Path, base_dir: Path = REPO_ROOT) -> str:
    return path.resolve().relative_to(base_dir.resolve()).as_posix()


def compute_corpus_version(documents: Iterable[ManifestDocument]) -> str:
    """Deterministic hash of the manifest's document-identity fields — same
    corpus contents always hashes the same, regardless of iteration order or
    of anything that isn't part of `ManifestDocument.identity_key()`."""
    keys = sorted(json.dumps(doc.identity_key(), ensure_ascii=True) for doc in documents)
    canonical = "\n".join(keys)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_TRAILING_NUMBER_RE = re.compile(
    r"\s+(?:n[º°o]\.?\s*)?[\d./-]+(?:\s*-\s*[a-zçãõáéíóúâêô]+)?$",
    re.IGNORECASE,
)


def normalize_tipo_documento(raw: str) -> str:
    """Strip a trailing document number/date suffix (e.g. `"Carta 65"` ->
    `"Carta"`, `"Despacho de Mero Expediente 214"` -> `"Despacho de Mero
    Expediente"`) so triage rules match the *kind* of document, not one
    specific numbered instance. See triage.py for how this is used."""
    normalized = raw.strip()
    previous = None
    while previous != normalized:
        previous = normalized
        normalized = _TRAILING_NUMBER_RE.sub("", normalized).strip()
    return normalized
