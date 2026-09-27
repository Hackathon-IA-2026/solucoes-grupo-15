"""Unit tests for triage.py (issue #68) — the discard-before-extraction
policy. **The policy itself (DISCARD_TIPOS/DISCARD_FORMATOS) must be
approved by Eduardo** before the batch executor runs over a full category;
these tests only check the mechanics are correct, not that the list is the
final word.

Run with: python3.12 -m pytest hackathon/tools/pipeline/test_triage.py -q
"""

from __future__ import annotations

import pytest

from manifest import ManifestDocument
from triage import apply_triage, triage_document


def _doc(
    tipo_documento: str,
    categoria: str = "01 Encargos rescisorios CUST x RAP transmissoras",
    formato: str = "pdf",
) -> ManifestDocument:
    return ManifestDocument(
        corpus_id="processos-aneel",
        categoria=categoria,
        processo="48500.000000/2026-00",
        numero_sei="0000000",
        tipo_documento=tipo_documento,
        data="01/01/2026",
        caminho="hackathon/data/x.pdf",
        formato=formato,
        bytes=100,
        sha256="a" * 64,
        status_origem="ok",
    )


@pytest.mark.parametrize(
    "tipo_documento",
    [
        "Recibo",
        "Recibo Registrado",
        "Recibo do",
        "Procuração",
        "Requerimento de Distribuição de Processo",
        "Despacho de Distribuição de Processo",
        "Requerimento de Inclusão em Pauta",
        "Despacho de Mero Expediente 214",
        "Formulário",
        "Documentação Societária",
        "Termo de Cancelamento de Documento",
        "Confirmação",
        "Confirmação do Recebimento de Notificação",
        "Lista de Presença",
        "CNPJ",
        "CNH",
        "Recibo 42",  # numbered variant must still normalize to "Recibo"
    ],
)
def test_discards_no_search_value_types(tipo_documento: str):
    decision = triage_document(_doc(tipo_documento))
    assert decision.descartado is True
    assert decision.motivo


@pytest.mark.parametrize(
    "tipo_documento",
    [
        "Carta",
        "Contrato",
        "Voto",
        "Nota Técnica",
        "Extrato da Decisão da Diretoria",
        "Auto de Infração",
        "Despacho",  # generic Despacho (substantive) must survive, only the
        # "de Mero Expediente"/"de Distribuição de Processo" variants go
        "Termo de Arquivamento",  # carries process-status info Carolina wants
        "Anexo I",
    ],
)
def test_keeps_types_with_search_value(tipo_documento: str):
    decision = triage_document(_doc(tipo_documento))
    assert decision.descartado is False
    assert decision.motivo is None


def test_contrato_never_discarded_even_in_category_01():
    # Issue #68's own warning: category 01's "Contrato" is a real CUST
    # contract, not "contrato social" — never discard it.
    decision = triage_document(
        _doc("Contrato", categoria="01 Encargos rescisorios CUST x RAP transmissoras")
    )
    assert decision.descartado is False


@pytest.mark.parametrize("formato", ["jpeg", "jpg", "jfif", "png", "mp4", "mp3"])
def test_discards_media_formats_regardless_of_tipo_documento(formato: str):
    # A substantive-sounding tipo_documento does not save a media file — the
    # format check runs first.
    decision = triage_document(_doc("Nota Técnica", formato=formato))
    assert decision.descartado is True


def test_apply_triage_returns_new_objects_without_mutating_input():
    original = _doc("Recibo")
    result = apply_triage([original])
    assert original.descartado is False  # input untouched
    assert result[0].descartado is True
    assert result[0] is not original
