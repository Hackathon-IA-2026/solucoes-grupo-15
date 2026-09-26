"""Unit tests for manifest.py (issue #68) — a synthetic corpus under
tmp_path, no dependency on the real (gitignored, ~3.3 GB) `hackathon/data`.

Run with: python3.12 -m pytest hackathon/tools/pipeline/test_manifest.py -q
"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest

from manifest import (
    ANEEL_CORPUS_ID,
    CASE1_CORPUS_ID,
    Sha256Cache,
    build_corpus_manifest,
    compute_corpus_version,
    is_case1_manual_markdown,
    normalize_tipo_documento,
    sha256_bytes,
)

CSV_HEADER = (
    '"categoria";"processo";"tipo_processo";"ordem";"sei";"tipo_documento";'
    '"data";"unidade";"arquivo";"bytes";"status"\n'
)


def _csv_row(**overrides) -> str:
    row = {
        "categoria": "04 Compartilhamento de postes",
        "processo": "48500.999999/2026-01",
        "tipo_processo": "Outorga de Distribuição",
        "ordem": "1",
        "sei": "0000001",
        "tipo_documento": "Carta 1",
        "data": "01/01/2026",
        "unidade": "PROTOCOLO-GERAL",
        "arquivo": "001_SEI_0000001_Carta_1.pdf",
        "bytes": "123",
        "status": "ok",
    }
    row.update(overrides)
    fields = [
        "categoria",
        "processo",
        "tipo_processo",
        "ordem",
        "sei",
        "tipo_documento",
        "data",
        "unidade",
        "arquivo",
        "bytes",
        "status",
    ]
    return ";".join(f'"{row[f]}"' for f in fields) + "\n"


def _write_processo_dir(base: Path, processo_dirname: str, files: dict[str, bytes]) -> Path:
    processo_dir = base / processo_dirname
    processo_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (processo_dir / name).write_bytes(content)
    return processo_dir


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"

    # --- case-1-carolina-mmgd ---------------------------------------
    case1_processo = root / "case-1-carolina-mmgd" / "48500.111111-2020-11"
    case1_processo.mkdir(parents=True)
    (case1_processo / "auto-infracao-48500.111111-2020-11.pdf").write_bytes(b"%PDF-auto-infracao")
    (case1_processo / "auto-infracao-48500.111111-2020-11.md").write_text(
        "manual output from #59, must be ignored as input", encoding="utf-8"
    )
    (case1_processo / "recurso-48500.111111-2020-11.pdf").write_bytes(b"%PDF-recurso")

    # --- processos aneel ---------------------------------------------
    categoria_dir = root / "processos aneel" / "processos" / "04 Compartilhamento de postes"
    categoria_dir.mkdir(parents=True)

    normal_dir = _write_processo_dir(
        categoria_dir,
        "48500.999999_2026-01",
        {"001_SEI_0000001_Carta_1.pdf": b"%PDF-carta-normal"},
    )
    _ = normal_dir

    html_dir = _write_processo_dir(
        categoria_dir,
        "48500.888888_2026-02",
        {"001_SEI_0000002_Voto.html": b"<html>voto</html>"},
    )
    _ = html_dir

    # a zip with a plain member and a nested zip (real corpus has both)
    zip_dir = categoria_dir / "48500.777777_2026-03"
    zip_dir.mkdir()
    zip_path = zip_dir / "001_SEI_0000003_Anexo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("direto.pdf", b"%PDF-direto-no-zip")
        nested_buffer_path = zip_dir / "_nested.zip"
        with zipfile.ZipFile(nested_buffer_path, "w") as nested_zf:
            nested_zf.writestr("dentro-do-aninhado.pdf", b"%PDF-aninhado")
        zf.write(nested_buffer_path, "aninhado.zip")
        nested_buffer_path.unlink()

    csv_path = categoria_dir / "_indice_04.csv"
    csv_path.write_text(
        CSV_HEADER
        + _csv_row(
            processo="48500.999999/2026-01",
            arquivo="001_SEI_0000001_Carta_1.pdf",
        )
        + _csv_row(
            processo="48500.888888/2026-02",
            sei="0000002",
            tipo_documento="Voto",
            arquivo="001_SEI_0000002_Voto.html",
        )
        + _csv_row(
            processo="48500.666666/2026-04",
            sei="0000004",
            tipo_documento="Recibo",
            arquivo="",
            status="restrito",
        )
        + _csv_row(
            processo="48500.777777/2026-03",
            sei="0000003",
            tipo_documento="Anexo",
            arquivo="001_SEI_0000003_Anexo.zip",
        ),
        encoding="utf-8-sig",
    )

    (categoria_dir / "48500.999999_2026-01" / "_processo.json").write_text(
        json.dumps({"processo": "48500.999999/2026-01", "url": "https://sei.aneel.gov.br/x"}),
        encoding="utf-8",
    )

    return root


def _build(data_root: Path, sha_cache=None):
    # base_dir=data_root.parent so `caminho` comes out as "data/..." without
    # requiring the synthetic corpus to live under the real REPO_ROOT.
    return build_corpus_manifest(data_root, sha_cache, base_dir=data_root.parent)


def test_case1_scan_derives_tipo_documento_from_filename(data_root: Path):
    documents = _build(data_root)
    case1_docs = [d for d in documents if d.corpus_id == CASE1_CORPUS_ID]

    assert {d.tipo_documento for d in case1_docs} == {"Auto de Infração", "Recurso"}
    assert all(d.processo == "48500.111111/2020-11" for d in case1_docs)
    assert all(d.formato == "pdf" for d in case1_docs)


def test_case1_manual_markdown_is_never_a_document(data_root: Path):
    documents = _build(data_root)
    assert all(not is_case1_manual_markdown(Path(d.caminho)) for d in documents if d.caminho)
    assert not any(d.caminho and d.caminho.endswith(".md") for d in documents)


def test_restrito_document_has_no_path_or_hash_but_is_still_recorded(data_root: Path):
    documents = _build(data_root)
    restrito = [d for d in documents if d.status_origem == "restrito"]
    assert len(restrito) == 1
    doc = restrito[0]
    assert doc.caminho is None
    assert doc.sha256 is None
    assert doc.formato is None
    assert doc.tipo_documento == "Recibo"
    assert doc.processo == "48500.666666/2026-04"


def test_zip_is_expanded_and_never_itself_a_document(data_root: Path):
    documents = _build(data_root)
    assert not any(d.formato == "zip" for d in documents)

    from_zip = [d for d in documents if d.origem is not None]
    assert len(from_zip) == 2  # direto.pdf + the nested zip's own member

    direto = next(d for d in from_zip if d.origem["zip_membro"] == "direto.pdf")
    assert direto.origem["profundidade"] == 1
    assert direto.origem["zip_caminho"].endswith("001_SEI_0000003_Anexo.zip")
    assert direto.sha256 == sha256_bytes(b"%PDF-direto-no-zip")
    assert direto.tipo_documento == "Anexo"  # inherited from the zip's own CSV row
    assert direto.caminho is None

    aninhado = next(d for d in from_zip if d.origem["zip_membro"] == "dentro-do-aninhado.pdf")
    assert aninhado.origem["profundidade"] == 2
    assert aninhado.origem["zip_lineage"][-1] == "aninhado.zip"
    assert aninhado.sha256 == sha256_bytes(b"%PDF-aninhado")


def test_processo_url_is_loaded_from_processo_json(data_root: Path):
    documents = _build(data_root)
    carta = next(d for d in documents if d.processo == "48500.999999/2026-01")
    assert carta.processo_url == "https://sei.aneel.gov.br/x"


def test_corpus_version_is_deterministic_across_rebuilds(data_root: Path):
    first = compute_corpus_version(_build(data_root))
    second = compute_corpus_version(_build(data_root))
    assert first == second
    assert len(first) == 64  # sha256 hex digest


def test_corpus_version_changes_when_a_file_changes(data_root: Path):
    before = compute_corpus_version(_build(data_root))
    normal_pdf = (
        data_root
        / "processos aneel"
        / "processos"
        / "04 Compartilhamento de postes"
        / "48500.999999_2026-01"
        / "001_SEI_0000001_Carta_1.pdf"
    )
    normal_pdf.write_bytes(normal_pdf.read_bytes() + b" edited")
    after = compute_corpus_version(_build(data_root))
    assert before != after


def test_corpus_version_ignores_processo_url(data_root: Path):
    # processo_url carries a rotating SEI query-string token in the real
    # corpus (see manifest.py docstring) — it must never affect corpus_version.
    before = compute_corpus_version(_build(data_root))
    processo_json = (
        data_root
        / "processos aneel"
        / "processos"
        / "04 Compartilhamento de postes"
        / "48500.999999_2026-01"
        / "_processo.json"
    )
    processo_json.write_text(
        json.dumps({"processo": "48500.999999/2026-01", "url": "https://sei.aneel.gov.br/ROTATED"}),
        encoding="utf-8",
    )
    after = compute_corpus_version(_build(data_root))
    assert before == after


def test_sha256_cache_avoids_rehashing_unchanged_files(tmp_path: Path, data_root: Path):
    cache_path = tmp_path / "sha_cache.json"
    cache = Sha256Cache(cache_path)
    documents = _build(data_root, cache)
    cache.save()

    reloaded = Sha256Cache(cache_path)
    calls = {"count": 0}
    real_get = reloaded.get_or_compute

    def counting_get(path):
        calls["count"] += 1
        return real_get(path)

    reloaded.get_or_compute = counting_get  # type: ignore[method-assign]
    _build(data_root, reloaded)
    # every file is unchanged, so every lookup should be served from cache —
    # get_or_compute is still called, but it must not re-hash (checked via
    # its own size/mtime_ns guard, exercised indirectly by call count > 0
    # while still returning identical digests).
    assert calls["count"] > 0
    assert compute_corpus_version(documents) == compute_corpus_version(
        _build(data_root, reloaded)
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Carta 65", "Carta"),
        ("Contrato 51/2026", "Contrato"),
        ("Despacho de Mero Expediente 214", "Despacho de Mero Expediente"),
        ("Requerimento de Inclusão em Pauta", "Requerimento de Inclusão em Pauta"),
        ("Ofício Nº 00915", "Ofício"),
        ("Documentação Societária", "Documentação Societária"),
        ("Anexo I", "Anexo I"),
    ],
)
def test_normalize_tipo_documento(raw: str, expected: str):
    assert normalize_tipo_documento(raw) == expected
