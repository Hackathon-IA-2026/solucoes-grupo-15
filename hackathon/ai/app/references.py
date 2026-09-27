"""Extracao de referencias explicitas do texto indexado - ``references[]``
do ``IndexReport`` (issue #92; contrato em
requirements/contracts/backend-vector-service.md, decisao issue-4 em
d14-data-operations-modeling).

Cada referencia e ``{identifier_raw, relation_type, locator}``:

- ``identifier_raw``: o trecho citado, com espacos/quebras de linha
  normalizados para um espaco (o backend resolve o identificador para um
  ``family_id`` pela chave ``tipo + identificador oficial``; o ai nunca
  resolve ids);
- ``relation_type``: sempre ``None`` por enquanto - os padroes textuais
  dos tipos finos (``revoga``, ``altera``, ``responde_a``, ``regula``)
  seguem em aberto em d14, entao o backend grava a aresta generica
  ``referencia``;
- ``locator``: o ``chunk_id`` (issue #96) do chunk onde a citacao foi
  encontrada.

Reconhecedor deliberadamente estreito: so "Auto de Infração [– AI –] nº
<numero>/<ano>[-<sigla>]", o unico identificador oficial validado contra
o texto real do caso 1 (os ``document_id`` dos autos no catalogo sao
"AI <numero>/<ano>-<sigla>"). Leis, resolucoes e demais tipos ficam para
quando seus padroes forem definidos (questao aberta de d14).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.chunking import Chunk

_AUTO_DE_INFRACAO_RE = re.compile(
    r"(?i:auto\s+de\s+infra[çc][ãa]o)"
    r"(?:\s*[–-]\s*AI\s*[–-])?"
    r"\s*n[º°o]\.?\s*"
    r"\d{1,4}/\d{4}"
    r"(?:-[A-Z]{2,4}(?![A-Za-z]))?"
)


@dataclass(frozen=True)
class Reference:
    identifier_raw: str
    relation_type: str | None
    locator: str


def extract_references(chunks: list[Chunk]) -> list[Reference]:
    """Referencias na ordem do documento, uma por ``(identifier_raw,
    locator)`` - a sobreposicao entre chunks vizinhos pode repetir a mesma
    citacao com outro ``locator``, e as duas ocorrencias sao evidencia."""
    references: list[Reference] = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        for match in _AUTO_DE_INFRACAO_RE.finditer(chunk.text):
            identifier = " ".join(match.group(0).split())
            key = (identifier, chunk.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            references.append(Reference(identifier, None, chunk.chunk_id))
    return references
