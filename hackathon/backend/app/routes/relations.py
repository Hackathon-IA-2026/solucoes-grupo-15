"""Rotas publicas do grafo de relacoes e da pagina de processo (TB1
Ticket 5, issue #21).

``GET /v1/documents/{node_id}/graph`` devolve as arestas de um no
(familia ou processo) em ``document_relations`` - em ambas as
direcoes (o no consultado pode ser ``source_id`` ou ``target_id`` de
uma aresta), cada uma com o vizinho ja resolvido do lado oposto. Toda
aresta desta issue tem ``origin: "explicit"``/``status: "confirmed"``
(nenhum fluxo de aceitar/rejeitar existe aqui - isso pertence ao
Ticket opcional #22).

Resolucao de ``node_id`` (familia vs. processo, decisao documentada no
resumo de entrega): tenta ``document_family`` primeiro (existe no
catalogo -> ``"family"``); senao, verifica se o id bate com algum
``processo_numero`` conhecido em ``document_version`` (-> ``"processo"``);
senao, cai para inspecionar ``document_relations`` diretamente (o
``source_kind``/``target_kind`` da primeira aresta que cita esse id) -
cobre o caso teorico de uma aresta citar um no que nao esta (mais) no
catalogo. Nenhuma dessas fontes cita o id -> 404.

``node_id``/``processo_id`` usam o conversor ``:path`` do Starlette
(``{node_id:path}``) porque um numero de processo SEI real contem "/"
(ex. "48500.001234/2024-11") - sem isso, o proprio id nao caberia num
unico segmento de rota.

``GET /v1/processos/{processo_id}`` lista as pecas de um processo
(familias ligadas por ``pertence_ao_processo`` com
``target_id == processo_id``), cada uma com a data representativa (a
face da familia, via ``select_face_version`` - mesmo helper usado por
POST /v1/search e GET /v1/documents/{family_id}), ordenadas por essa
data; inclui tambem as arestas ``responde_a`` entre pecas do mesmo
processo, para o frontend desenhar a cadeia. Processo sem nenhuma
aresta ``pertence_ao_processo`` -> 404.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.catalog import select_face_version
from app.db import get_db_session
from app.models import DocumentFamily, DocumentRelation, DocumentVersion

router = APIRouter(prefix="/v1", tags=["relations"])


class EvidenceOut(BaseModel):
    document_version: str
    locator: str


class GraphEdgeOut(BaseModel):
    type: str
    origin: str
    status: str
    neighbor_id: str
    neighbor_kind: str
    evidence: EvidenceOut | None


class GraphOut(BaseModel):
    node_id: str
    node_kind: str
    edges: list[GraphEdgeOut]


class ProcessoPieceOut(BaseModel):
    family_id: str
    document_type: str
    document_id: str
    version_date: str


class RespondeAEdgeOut(BaseModel):
    source_family_id: str
    target_family_id: str
    evidence: EvidenceOut | None


class ProcessoOut(BaseModel):
    processo_id: str
    pieces: list[ProcessoPieceOut]
    responde_a: list[RespondeAEdgeOut]


class ProcessoSummaryOut(BaseModel):
    processo_id: str
    latest_movement_at: str
    latest_document_type: str
    latest_document_id: str
    pieces_count: int
    document_types: list[str]


@router.get("/documents/{node_id:path}/graph", response_model=GraphOut)
def get_graph(node_id: str, session: Session = Depends(get_db_session)) -> GraphOut:
    node_kind = _resolve_node_kind(session, node_id)
    if node_kind is None:
        raise HTTPException(status_code=404, detail="No nao encontrado")

    edges = session.scalars(
        select(DocumentRelation).where(
            or_(
                DocumentRelation.source_id == node_id,
                DocumentRelation.target_id == node_id,
            )
        )
    ).all()

    return GraphOut(
        node_id=node_id,
        node_kind=node_kind,
        edges=[_to_graph_edge(edge, node_id) for edge in edges],
    )


@router.get("/processos", response_model=list[ProcessoSummaryOut])
def list_processos(session: Session = Depends(get_db_session)) -> list[ProcessoSummaryOut]:
    membership_edges = session.scalars(
        select(DocumentRelation).where(
            DocumentRelation.type == "pertence_ao_processo",
            DocumentRelation.target_kind == "processo",
        )
    ).all()

    families_by_process: dict[str, list[str]] = {}
    for edge in membership_edges:
        families_by_process.setdefault(edge.target_id, []).append(edge.source_id)

    summaries: list[ProcessoSummaryOut] = []
    for processo_id, family_ids in families_by_process.items():
        pieces = _pieces_for_families(session, family_ids)
        if not pieces:
            continue
        latest = max(pieces, key=lambda piece: piece.version_date)
        summaries.append(
            ProcessoSummaryOut(
                processo_id=processo_id,
                latest_movement_at=latest.version_date,
                latest_document_type=latest.document_type,
                latest_document_id=latest.document_id,
                pieces_count=len(pieces),
                document_types=sorted({piece.document_type for piece in pieces}),
            )
        )

    return sorted(
        summaries,
        key=lambda item: (item.latest_movement_at, item.processo_id),
        reverse=True,
    )


@router.get("/processos/{processo_id:path}", response_model=ProcessoOut)
def get_processo(processo_id: str, session: Session = Depends(get_db_session)) -> ProcessoOut:
    membership_edges = session.scalars(
        select(DocumentRelation).where(
            DocumentRelation.type == "pertence_ao_processo",
            DocumentRelation.target_id == processo_id,
            DocumentRelation.target_kind == "processo",
        )
    ).all()
    if not membership_edges:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")

    family_ids = [edge.source_id for edge in membership_edges]
    pieces = _pieces_for_families(session, family_ids)
    pieces.sort(key=lambda piece: piece.version_date)

    responde_a = _responde_a_between(session, set(family_ids))

    return ProcessoOut(processo_id=processo_id, pieces=pieces, responde_a=responde_a)


def _resolve_node_kind(session: Session, node_id: str) -> str | None:
    if session.get(DocumentFamily, node_id) is not None:
        return "family"

    known_processos = session.scalars(
        select(DocumentVersion.processo_numero).where(
            DocumentVersion.processo_numero.isnot(None)
        )
    ).all()
    if node_id in known_processos:
        return "processo"

    edge = session.scalar(
        select(DocumentRelation).where(
            or_(
                DocumentRelation.source_id == node_id,
                DocumentRelation.target_id == node_id,
            )
        )
    )
    if edge is None:
        return None
    return edge.source_kind if edge.source_id == node_id else edge.target_kind


def _to_graph_edge(edge: DocumentRelation, node_id: str) -> GraphEdgeOut:
    if edge.source_id == node_id:
        neighbor_id, neighbor_kind = edge.target_id, edge.target_kind
    else:
        neighbor_id, neighbor_kind = edge.source_id, edge.source_kind

    return GraphEdgeOut(
        type=edge.type,
        origin=edge.origin,
        status=edge.status,
        neighbor_id=neighbor_id,
        neighbor_kind=neighbor_kind,
        evidence=_evidence_out(edge),
    )


def _evidence_out(edge: DocumentRelation) -> EvidenceOut | None:
    if edge.evidence_document_version is None:
        return None
    return EvidenceOut(
        document_version=edge.evidence_document_version,
        locator=edge.evidence_locator or "",
    )


def _pieces_for_families(session: Session, family_ids: list[str]) -> list[ProcessoPieceOut]:
    pieces: list[ProcessoPieceOut] = []
    for family_id in family_ids:
        versions = session.scalars(
            select(DocumentVersion).where(DocumentVersion.family_id == family_id)
        ).all()
        if not versions:
            # Aresta cita uma familia ausente do catalogo - nao deveria
            # acontecer com a fixture consistente; pula em vez de quebrar
            # a pagina do processo inteira.
            continue
        face = select_face_version(versions)
        pieces.append(
            ProcessoPieceOut(
                family_id=family_id,
                document_type=face.document_type,
                document_id=face.document_id,
                version_date=face.version_date,
            )
        )
    return pieces


def _responde_a_between(session: Session, family_ids: set[str]) -> list[RespondeAEdgeOut]:
    edges = session.scalars(
        select(DocumentRelation).where(
            DocumentRelation.type == "responde_a",
            DocumentRelation.source_kind == "family",
            DocumentRelation.target_kind == "family",
        )
    ).all()
    return [
        RespondeAEdgeOut(
            source_family_id=edge.source_id,
            target_family_id=edge.target_id,
            evidence=_evidence_out(edge),
        )
        for edge in edges
        if edge.source_id in family_ids and edge.target_id in family_ids
    ]
