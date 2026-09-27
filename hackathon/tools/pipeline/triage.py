"""Triage: mark manifest documents with no search value as discarded,
*before* any extraction runs (issue #68).

This policy list was assembled by scanning `tipo_documento` across every
`_indice_*.csv` in `hackathon/data/processos aneel/processos/` (2195 rows,
5 categories) and grouping by `normalize_tipo_documento` (see
`manifest.py`). **It must be approved by Eduardo before the batch executor
runs over a full category** — that approval is acceptance criterion #3 of
issue #68, tracked outside this file (the issue/evidence-pack comment).

Explicitly investigated per the issue's own warning: "Contrato" in category
`01 Encargos rescisórios CUST x RAP transmissoras` is a real CUST
(Contrato de Uso do Sistema de Transmissão) contract, not "contrato
social". Checked against the real data: ANEEL's own `tipo_documento`
already separates those — corporate/incorporation paperwork is filed under
the distinct type `"Documentação Societária"`, never under `"Contrato"`.
So this policy discards `"Documentação Societária"` and never discards any
`"Contrato*"` type, in any category.
"""

from __future__ import annotations

from dataclasses import dataclass

from manifest import ManifestDocument, normalize_tipo_documento

# tipo_documento (normalized, case-insensitive) -> reason shown in reports.
# Matches the issue's own candidate list plus the exact-variant spellings
# found in the real corpus (e.g. "Recibo Registrado", "Recibo do").
DISCARD_TIPOS: dict[str, str] = {
    "recibo": "recibo de protocolo/entrega, sem conteúdo de mérito",
    "recibo registrado": "recibo de protocolo/entrega, sem conteúdo de mérito",
    "recibo do": "recibo de protocolo/entrega, sem conteúdo de mérito",
    "recibo (s)": "recibo de protocolo/entrega, sem conteúdo de mérito",
    "procuração": "instrumento de representação, sem conteúdo de mérito",
    "requerimento de distribuição de processo": (
        "trâmite administrativo interno (distribuição), sem conteúdo de mérito"
    ),
    "despacho de distribuição de processo": (
        "trâmite administrativo interno (distribuição), sem conteúdo de mérito"
    ),
    "requerimento de inclusão em pauta": (
        "trâmite administrativo interno (agenda de pauta), sem conteúdo de mérito"
    ),
    "despacho de mero expediente": (
        "despacho de mero expediente: ato processual sem conteúdo decisório"
    ),
    "formulário": "formulário de cadastro/entrada, sem conteúdo de mérito",
    "documentação societária": (
        'documentação de constituição societária ("contrato social" e similares) —'
        ' distinto de "Contrato" (ex.: CUST), nunca descartado'
    ),
    "termo de cancelamento de documento": (
        "termo administrativo de cancelamento de documento, sem conteúdo de mérito"
    ),
    "confirmação": "confirmação de recebimento, sem conteúdo de mérito",
    "confirmação do recebimento de notificação": (
        "confirmação de recebimento, sem conteúdo de mérito"
    ),
    "lista de presença": "lista de presença/registro de comparecimento, sem conteúdo de mérito",
    "cnpj": "documento de identificação de pessoa jurídica, sem conteúdo de mérito",
    "cnh": "documento de identificação pessoal, sem conteúdo de mérito",
}

# File formats that are media/images regardless of tipo_documento — the
# issue's "mídia e imagens" candidate.
DISCARD_FORMATOS: dict[str, str] = {
    "jpeg": "imagem, sem texto extraível",
    "jpg": "imagem, sem texto extraível",
    "jfif": "imagem, sem texto extraível",
    "png": "imagem, sem texto extraível",
    "mp4": "vídeo, sem rota de extração de texto",
    "mp3": "áudio, sem rota de extração de texto",
}


@dataclass(frozen=True)
class TriageDecision:
    descartado: bool
    motivo: str | None


def triage_document(doc: ManifestDocument) -> TriageDecision:
    """Decide whether `doc` should be discarded before extraction.

    Format check runs first: an image/video/audio file is discarded
    regardless of what `tipo_documento` ANEEL filed it under.
    """
    if doc.formato is not None:
        formato_reason = DISCARD_FORMATOS.get(doc.formato.lower())
        if formato_reason is not None:
            return TriageDecision(True, formato_reason)

    normalized = normalize_tipo_documento(doc.tipo_documento).casefold()
    tipo_reason = DISCARD_TIPOS.get(normalized)
    if tipo_reason is not None:
        return TriageDecision(True, tipo_reason)

    return TriageDecision(False, None)


def apply_triage(documents: list[ManifestDocument]) -> list[ManifestDocument]:
    """Return a new list with `descartado`/`motivo_descarte` populated on
    every document. Never mutates the input list's items in place, so a
    manifest built once can be triaged under more than one policy version
    for comparison."""
    triaged: list[ManifestDocument] = []
    for doc in documents:
        decision = triage_document(doc)
        triaged.append(
            ManifestDocument(
                **{
                    **doc.to_dict(),
                    "descartado": decision.descartado,
                    "motivo_descarte": decision.motivo,
                }
            )
        )
    return triaged
