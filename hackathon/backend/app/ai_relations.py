"""Arestas do grafo a partir dos candidatos do ai (issue #92).

O ai entrega so candidatos (contrato backend <-> ai,
requirements/contracts/backend-vector-service.md): ``references[]`` em
cada ``IndexReport`` e ``similar_families(family_id, top_k)``. Resolver
ids, aplicar limiares e gravar/curar ``document_relations`` e do backend
(i4-storage, d14-data-operations-modeling, i10-hybrid-decision-intelligence).
Roda no fim do job de ingestao (``run_ingestion``).

Vizinhanca vetorial -> ``similar_a``:

- ``LIMIAR_RELACAO <= score < LIMIAR_FUSAO`` -> aresta ``similar_a``,
  ``origin="similarity"``, ``status="suggested"``, com ``score``;
- ``score >= LIMIAR_FUSAO`` -> candidato a sugestao de fusao de familia
  (#3), nunca ``similar_a``. O backend ainda nao tem a maquina de
  sugestao de fusao (Ticket opcional #22), entao o candidato e so
  descartado aqui - nenhum par do caso 1 chega perto (teto 0,9278, #74);
- abaixo de ``LIMIAR_RELACAO`` -> descartado.

A vizinhanca e simetrica: o par e gravado uma vez so, com as pontas em
ordem lexicografica (``source_id < target_id``). Numa reingestao so o
``score`` e atualizado - ``status`` de uma aresta ja existente nunca e
sobrescrito, para nao desfazer uma decisao humana futura.

``LIMIAR_RELACAO = 0.80``, ``LIMIAR_FUSAO = 0.97`` e ``SIMILAR_TOP_K = 3``
sao os valores calibrados na issue #61 e reconfirmados na #74 contra os
embeddings reais do caso 1 (d14; evidencia em
hackathon/tools/case1_recall/similarity_calibration/). So valem para a
agregacao "media dos embeddings de chunk da familia" usada pelo ai.

Referencias explicitas -> ``referencia`` (ou o tipo fino que o ai mandar):

O identificador cru e resolvido para um ``family_id`` pela chave
``tipo + identificador oficial`` (#3). Por ora o unico tipo reconhecido e
o auto de infracao: chave ``(numero, ano, sigla?)``, comparada contra o
``document_id`` das versoes do catalogo (ex.: "AI 0017/2020-SFE",
"Exposicao de Motivos / AI 35/2025-SFT"). Numero sem zeros a esquerda;
se os dois lados tem sigla, ela precisa bater. A aresta nasce
``origin="explicit"``/``status="confirmed"`` com evidencia
``(document_version, locator)`` da primeira ocorrencia. Citacao da
propria familia, alvo ambiguo ou fora do corpus nao gera aresta (a
"aresta pendente de alvo" de d14 ainda nao tem representacao no schema).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.ai_client import AiClient, IndexReport
from app.fixtures.loader import FixtureCorpus
from app.models import DocumentFamily, DocumentRelation, DocumentVersion

LIMIAR_RELACAO = 0.80
LIMIAR_FUSAO = 0.97
SIMILAR_TOP_K = 3

EXPLICIT_RELATION_TYPES = {"referencia", "revoga", "altera", "responde_a", "regula"}

_AUTO_KEY_RE = re.compile(
    r"(?:(?i:auto\s+de\s+infra[çc][ãa]o)|\bAI\b)"
    r"(?:\s*[–-]\s*AI\s*[–-])?"
    r"\s*(?:n[º°o]\.?\s*)?"
    r"(\d{1,4})/(\d{4})"
    r"(?:-([A-Z]{2,4})(?![A-Za-z]))?"
)


@dataclass(frozen=True)
class _AutoKey:
    numero: int
    ano: int
    sigla: str | None

    def matches(self, other: _AutoKey) -> bool:
        if (self.numero, self.ano) != (other.numero, other.ano):
            return False
        return self.sigla is None or other.sigla is None or self.sigla == other.sigla


def auto_de_infracao_key(text: str) -> _AutoKey | None:
    """Chave do auto de infracao citado/identificado em ``text``, ou None."""
    match = _AUTO_KEY_RE.search(text)
    if match is None:
        return None
    numero, ano, sigla = match.groups()
    return _AutoKey(int(numero), int(ano), sigla)


@dataclass(frozen=True)
class _Edge:
    source_id: str
    target_id: str
    type: str
    origin: str
    status: str
    score: float | None = None
    evidence_document_version: str | None = None
    evidence_locator: str | None = None


def run_ai_relations(
    corpus: FixtureCorpus,
    reports_by_version: dict[str, IndexReport],
    *,
    ai_client: AiClient,
    session: Session,
) -> int:
    """Grava as arestas derivadas dos candidatos do ai; devolve quantas."""
    edges: dict[tuple[str, str, str], _Edge] = {}
    for edge in _reference_edges(corpus, reports_by_version, session):
        edges.setdefault((edge.source_id, edge.target_id, edge.type), edge)
    for edge in _similarity_edges(corpus, ai_client, session):
        edges.setdefault((edge.source_id, edge.target_id, edge.type), edge)

    for edge in edges.values():
        _upsert(session, edge)
    session.flush()
    return len(edges)


def _reference_edges(
    corpus: FixtureCorpus, reports_by_version: dict[str, IndexReport], session: Session
) -> list[_Edge]:
    catalog: list[tuple[_AutoKey, str]] = []
    for version in session.scalars(select(DocumentVersion)):
        key = auto_de_infracao_key(version.document_id or "")
        if key is not None:
            catalog.append((key, version.family_id))

    edges: list[_Edge] = []
    for doc in corpus.documents:
        for ref in reports_by_version[doc.document_version].references:
            cited = auto_de_infracao_key(ref.identifier_raw)
            if cited is None:
                continue
            targets = {family_id for key, family_id in catalog if cited.matches(key)}
            if len(targets) != 1:
                continue
            [target] = targets
            if target == doc.family_id:
                continue
            edges.append(
                _Edge(
                    source_id=doc.family_id,
                    target_id=target,
                    type=(
                        ref.relation_type
                        if ref.relation_type in EXPLICIT_RELATION_TYPES
                        else "referencia"
                    ),
                    origin="explicit",
                    status="confirmed",
                    evidence_document_version=doc.document_version,
                    evidence_locator=ref.locator,
                )
            )
    return edges


def _similarity_edges(
    corpus: FixtureCorpus, ai_client: AiClient, session: Session
) -> list[_Edge]:
    edges: list[_Edge] = []
    for family_id in sorted({doc.family_id for doc in corpus.documents}):
        for candidate in ai_client.similar_families(family_id, top_k=SIMILAR_TOP_K):
            if not LIMIAR_RELACAO <= candidate.score < LIMIAR_FUSAO:
                continue
            if session.get(DocumentFamily, candidate.family_id) is None:
                continue
            source, target = sorted((family_id, candidate.family_id))
            edges.append(
                _Edge(
                    source_id=source,
                    target_id=target,
                    type="similar_a",
                    origin="similarity",
                    status="suggested",
                    score=candidate.score,
                )
            )
    return edges


def _upsert(session: Session, edge: _Edge) -> None:
    existing = session.scalar(
        select(DocumentRelation).where(
            DocumentRelation.source_id == edge.source_id,
            DocumentRelation.source_kind == "family",
            DocumentRelation.target_id == edge.target_id,
            DocumentRelation.target_kind == "family",
            DocumentRelation.type == edge.type,
        )
    )
    if existing is None:
        existing = DocumentRelation(
            source_id=edge.source_id,
            source_kind="family",
            target_id=edge.target_id,
            target_kind="family",
            type=edge.type,
            origin=edge.origin,
            status=edge.status,
        )
        session.add(existing)
    existing.score = edge.score
    existing.evidence_document_version = edge.evidence_document_version
    existing.evidence_locator = edge.evidence_locator
