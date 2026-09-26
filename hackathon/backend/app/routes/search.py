"""Rota publica de busca (TB1 Ticket 3, issue #19).

POST /v1/search chama ``AiClient.search(query, top_k)`` - o ai resolve
a busca sozinho contra o proprio fixture declarativo (ver
hackathon/ai/app/routes/search.py) e devolve hits crus, ainda nao
agrupados. Esta rota agrupa esses hits por ``family_id``, preservando
a ordem de primeira ocorrencia na lista devolvida pelo ai (NUNCA
reordena por score - isso seria ranking real, fora de escopo desta
issue, ver issues #10-#14). Cada familia aparece no maximo uma vez na
resposta, mesmo que o ai tenha devolvido chunks de duas ou mais
versoes dessa familia.

Para cada familia agrupada, consulta o catalogo (Postgres, via
document_version/document_family) para montar:
  - ``face``: a versao com maior ``version_date`` daquela familia
    (comparacao de string funciona - formato ISO AAAA-MM-DD).
  - ``matched_chunks``: um item por chunk casado devolvido pelo ai
    para essa familia, na mesma ordem em que o ai os devolveu;
    ``is_latest`` e True so quando ``document_version`` == o
    ``document_version`` da face.

Envelope da resposta: ``request_id`` (uuid4 novo por chamada),
``data_mode: "demo"``, ``corpus_version`` (lido do
``DocumentVersion.corpus_version`` da primeira familia resolvida - cai
para ``Settings.default_corpus_version`` quando ``results`` fica
vazio, pois nao ha nenhuma familia da qual derivar), ``model_version``
(a mesma constante ``"fixture-demo"`` devolvida pelo ai - nunca
reinventada aqui), ``ranking_version`` (constante nova desta issue,
``RANKING_VERSION`` abaixo - nao ha ranking real, so identifica esta
versao de codigo/agrupamento para reprodutibilidade futura, issue #16
secao "Versionamento e reprodutibilidade").

Paginacao lazy (issue #76): o body aceita ``cursor`` (opaco, opcional)
e ``limit`` (default 10). Sem cursor: executa a busca no ai, persiste
todos os hits em ``SearchExecution`` e devolve o primeiro lote. Com
cursor valido: carrega os hits congelados do ``SearchExecution``
identificado pelo cursor sem chamar o ai, devolve o proximo lote.
Cursor invalido/expirado → HTTP 400. ``total`` e o numero de familias
unicas do conjunto congelado inteiro; ``next_cursor`` e nulo na ultima
pagina.

Ticket 9 (issue #25, reprodutibilidade) acrescenta a persistencia de
``SearchExecution`` (app/models.py) a cada chamada: alem do envelope
final, grava os hits CRUS devolvidos por ``ai_client.search`` (antes
do agrupamento por familia) - e o "vetor da consulta preservado" desta
fase demo, que ``app/replay.py::replay_search`` usa para reexecutar a
busca offline, sem chamar o ai de novo (ver i7-reproducibility).
"""

import base64
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import select_face_version
from app.clients.ai_client import AiClient, AiSearchHit, get_ai_client
from app.config import get_settings
from app.db import get_db_session
from app.models import DocumentVersion, SearchExecution

router = APIRouter(prefix="/v1", tags=["search"])

# Constante nova desta issue (nao ha ranking real): identifica o
# codigo/comportamento de agrupamento usado para montar a resposta,
# para reprodutibilidade futura (issue #16, "Versionamento e
# reprodutibilidade"). Documentada no resumo de entrega do Ticket 3.
RANKING_VERSION = "demo-ranking-v1"


# ---------------------------------------------------------------------------
# Cursor helpers (issue #76)
# ---------------------------------------------------------------------------

def _encode_cursor(request_id: str, offset: int) -> str:
    """Codifica (request_id, offset) como cursor opaco em base64 URL-safe."""
    raw = f"{request_id}:{offset}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, int]:
    """Decodifica o cursor opaco; levanta ValueError em qualquer falha."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        request_id, offset_str = raw.rsplit(":", 1)
        offset = int(offset_str)
    except Exception as exc:
        raise ValueError(f"Cursor invalido: {cursor!r}") from exc
    if not request_id:
        raise ValueError(f"Cursor invalido: request_id vazio em {cursor!r}")
    return request_id, offset


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

class SearchRequestIn(BaseModel):
    query: str
    top_k: int | None = None
    cursor: str | None = None
    limit: int = 10


class SearchFace(BaseModel):
    document_version: str
    version_date: str
    document_type: str
    document_id: str
    processo_numero: str | None


class MatchedChunk(BaseModel):
    document_version: str
    excerpt: str
    score: float
    is_latest: bool


class SearchResultOut(BaseModel):
    family_id: str
    face: SearchFace
    matched_chunks: list[MatchedChunk]


class SearchEnvelope(BaseModel):
    request_id: str
    data_mode: str
    corpus_version: str
    model_version: str
    ranking_version: str
    results: list[SearchResultOut]
    total: int
    next_cursor: str | None = None


# ---------------------------------------------------------------------------
# Rota principal
# ---------------------------------------------------------------------------

@router.post("/search", response_model=SearchEnvelope)
def search(
    payload: SearchRequestIn,
    ai_client: AiClient = Depends(get_ai_client),
    session: Session = Depends(get_db_session),
) -> SearchEnvelope:
    limit = payload.limit

    if payload.cursor is not None:
        # --- Continuacao: carrega hits congelados, nao chama o ai ---
        try:
            request_id, offset = _decode_cursor(payload.cursor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        execution = session.get(SearchExecution, request_id)
        if execution is None:
            raise HTTPException(
                status_code=400,
                detail=f"Cursor expirado ou invalido: nenhuma execucao encontrada para request_id={request_id!r}",
            )

        raw_hits = [AiSearchHit(**h) for h in json.loads(execution.raw_hits_json)]
        all_results, _ = _group_by_family(raw_hits, session)
        total = len(all_results)
        page_results = all_results[offset : offset + limit]

        next_offset = offset + limit
        next_cursor = _encode_cursor(request_id, next_offset) if next_offset < total else None

        return SearchEnvelope(
            request_id=execution.request_id,
            data_mode=execution.data_mode,
            corpus_version=execution.corpus_version,
            model_version=execution.model_version,
            ranking_version=execution.ranking_version,
            results=page_results,
            total=total,
            next_cursor=next_cursor,
        )

    # --- Primeira chamada: executa busca no ai, persiste, devolve primeiro lote ---
    ai_response = ai_client.search(payload.query, top_k=payload.top_k)
    all_results, corpus_version = _group_by_family(ai_response.hits, session)
    total = len(all_results)
    page_results = all_results[:limit]

    request_id = str(uuid.uuid4())
    next_offset = limit
    next_cursor = _encode_cursor(request_id, next_offset) if next_offset < total else None

    envelope = SearchEnvelope(
        request_id=request_id,
        data_mode="demo",
        corpus_version=corpus_version,
        model_version=ai_response.model_version,
        ranking_version=RANKING_VERSION,
        results=page_results,
        total=total,
        next_cursor=next_cursor,
    )

    _persist_search_execution(
        envelope,
        query=payload.query,
        raw_hits=ai_response.hits,
        all_results=all_results,
        session=session,
    )

    return envelope


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def _persist_search_execution(
    envelope: SearchEnvelope,
    *,
    query: str,
    raw_hits: list[AiSearchHit],
    all_results: list[SearchResultOut],
    session: Session,
) -> None:
    """Grava o registro de execucao desta busca (Ticket 9, issue #25).

    ``raw_hits`` sao os hits CRUS devolvidos pelo ai, antes do
    agrupamento por familia - e esse valor, nao ``envelope.results``
    (que pode ser um slice da primeira pagina), que
    ``app/replay.py::replay_search`` reusa para reexecutar a busca
    offline (ver docstring do modulo).

    ``response_json`` armazena o envelope da primeira pagina para
    auditoria/comparacao; replay usa raw_hits_json para recomputar.
    """
    session.add(
        SearchExecution(
            request_id=envelope.request_id,
            query=query,
            data_mode=envelope.data_mode,
            corpus_version=envelope.corpus_version,
            model_version=envelope.model_version,
            ranking_version=envelope.ranking_version,
            raw_hits_json=json.dumps([hit.model_dump() for hit in raw_hits]),
            response_json=envelope.model_dump_json(),
            code_reference=get_settings().code_reference,
        )
    )
    session.flush()


# ---------------------------------------------------------------------------
# Agrupamento por familia
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Rota de replay (issue #77)
# ---------------------------------------------------------------------------

class ReplayEnvelope(BaseModel):
    request_id: str
    recomputed_response: SearchEnvelope
    original_response: SearchEnvelope
    matches: bool


@router.post("/search/{request_id}/replay", response_model=ReplayEnvelope)
def replay(
    request_id: str,
    session: Session = Depends(get_db_session),
) -> ReplayEnvelope:
    """Reexecuta, sem rede nem IA, a busca registrada sob ``request_id``.

    Chama ``app.replay.replay_search`` (lazy import para evitar ciclo:
    replay.py importa de routes/search.py). Retorna o envelope
    recomputado, o envelope original persistido e um booleano
    ``matches`` indicando se os dois coincidem.
    """
    # Lazy import para evitar ciclo: replay.py importa de routes/search.py
    from app.replay import SearchExecutionNotFound, replay_search  # noqa: PLC0415

    try:
        result = replay_search(request_id, session)
    except SearchExecutionNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma execucao de busca encontrada para request_id={request_id!r}",
        ) from exc

    return ReplayEnvelope(
        request_id=result.request_id,
        recomputed_response=result.recomputed_response,
        original_response=result.original_response,
        matches=result.matches,
    )


def _group_by_family(
    hits: list[AiSearchHit], session: Session
) -> tuple[list[SearchResultOut], str]:
    order: list[str] = []
    grouped: dict[str, list[AiSearchHit]] = {}
    for hit in hits:
        if hit.family_id not in grouped:
            grouped[hit.family_id] = []
            order.append(hit.family_id)
        grouped[hit.family_id].append(hit)

    results: list[SearchResultOut] = []
    corpus_version: str | None = None

    for family_id in order:
        family_hits = grouped[family_id]
        versions = session.scalars(
            select(DocumentVersion).where(DocumentVersion.family_id == family_id)
        ).all()
        if not versions:
            # O ai devolveu um family_id ausente do catalogo - nao deveria
            # acontecer com o corpus fixture consistente; pula essa familia
            # em vez de quebrar a busca inteira.
            continue

        face_version = select_face_version(versions)
        if corpus_version is None:
            corpus_version = face_version.corpus_version

        matched_chunks = [
            MatchedChunk(
                document_version=hit.document_version,
                excerpt=hit.excerpt,
                score=hit.score,
                is_latest=hit.document_version == face_version.document_version,
            )
            for hit in family_hits
        ]
        results.append(
            SearchResultOut(
                family_id=family_id,
                face=SearchFace(
                    document_version=face_version.document_version,
                    version_date=face_version.version_date,
                    document_type=face_version.document_type,
                    document_id=face_version.document_id,
                    processo_numero=face_version.processo_numero,
                ),
                matched_chunks=matched_chunks,
            )
        )

    if corpus_version is None:
        corpus_version = get_settings().default_corpus_version

    return results, corpus_version
