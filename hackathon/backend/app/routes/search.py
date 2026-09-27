"""Rota publica de busca (TB1 Ticket 3, issue #19; paginacao #76; replay #77;
busca por chunk #78).

POST /v1/search chama ``AiClient.search(query, top_k)`` - o ai resolve
a busca sozinho contra o proprio fixture declarativo e devolve hits crus,
ainda nao agrupados. Desde a issue #78, esta rota nao agrupa mais por
``family_id``: cada hit do ai vira um card separado (``SearchResultOut``
representa um chunk, nao uma familia).

Cada resultado carrega: ``family_id``, ``document_version``, ``excerpt``,
``score``, ``localizador`` (``extracted_text_locator`` da
``DocumentVersion``), ``document_type``, ``document_id``,
``processo_numero``, ``version_date``, ``chunk_id`` e ``chunk_index``
(issue #96: id estavel do chunk no indice e indice real do chunk dentro
do documento, 0-based, ambos vindos do ai - nunca a posicao do hit na
lista; ``(document_version, chunk_index)`` e a chave de chunk usada pelo
feedback, #82).

Envelope da resposta: ``request_id`` (uuid4 novo por chamada),
``data_mode`` (issue #69: ``"demo"`` quando ``Settings.embedder ==
"fake"`` - o mesmo toggle ``EMBEDDER`` do backend/ai, ver
app/config.py -, ``"real"`` quando ``"bedrock"`` - nunca mais fixo em
``"demo"``, ja que agora existe um modo com busca vetorial de
verdade), ``corpus_version`` (lido do ``DocumentVersion.corpus_version``
da primeira familia resolvida - cai para ``Settings.default_corpus_version``
quando ``results`` fica vazio, pois nao ha nenhuma familia da qual
derivar), ``model_version`` (a mesma constante devolvida pelo ai -
``"fixture-demo"`` no modo fake, a constante real do Titan V2 no modo
bedrock - nunca reinventada aqui), ``ranking_version`` (constante nova
desta issue, ``RANKING_VERSION`` abaixo - nao ha ranking real, so
identifica esta versao de codigo/agrupamento para reprodutibilidade
futura, issue #16 secao "Versionamento e reprodutibilidade").

Ordem total obrigatoria (issue #78): ``(-score, document_version,
chunk_index)`` — score decrescente, desempate lexicografico por
``document_version``, desempate final pelo indice real do chunk no
documento (issue #96).

``family_id`` permanece em cada resultado como atributo de filtro/dado,
mas **nao colapsa** resultados: o mesmo hit devolvido duas vezes pelo ai
aparece duas vezes.

Paginacao lazy (issue #76): body aceita ``cursor`` (opaco, opcional) e
``limit`` (default 10). Sem cursor: executa a busca no ai, persiste todos
os hits em ``SearchExecution`` e devolve o primeiro lote. Com cursor valido:
carrega os hits congelados do ``SearchExecution`` identificado pelo cursor
sem chamar o ai, devolve o proximo lote. Cursor invalido/expirado → HTTP
400. ``total`` e o numero de chunks (hits) do conjunto congelado inteiro;
``next_cursor`` e nulo na ultima pagina. ``data_mode`` e derivado uma unica
vez, na primeira chamada, e persistido em ``SearchExecution`` — a
continuacao por cursor devolve ``execution.data_mode`` congelado, nunca
recalcula a partir do ``Settings.embedder`` corrente (evita uma pagina 2
com ``data_mode`` diferente da pagina 1 se o toggle mudar entre chamadas).

Ticket 9 (issue #25, reprodutibilidade) acrescenta a persistencia de
``SearchExecution`` a cada chamada: alem do envelope final, grava os hits
CRUS devolvidos por ``ai_client.search`` (antes do agrupamento) - e o
"vetor da consulta preservado" desta fase demo, que
``app/replay.py::replay_search`` usa para reexecutar a busca offline,
sem chamar o ai de novo.
"""

import base64
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.ai_client import AiClient, AiSearchHit, get_ai_client
from app.config import get_settings
from app.db import get_db_session
from app.models import DocumentVersion, SearchExecution

router = APIRouter(prefix="/v1", tags=["search"])

# Constante de versao de ranking (issue #19); identifica este comportamento
# para reprodutibilidade futura (issue #16).
RANKING_VERSION = "demo-ranking-v1"


def _data_mode_for(embedder: str) -> str:
    """Deriva ``data_mode`` do toggle ``EMBEDDER`` (issue #69).

    ``"fake"`` (default) -> ``"demo"`` (nunca houve busca vetorial
    real). ``"bedrock"`` -> ``"real"``. ``"cached"`` (issue #88) ->
    ``"real"``: o ai roda o mesmo pipeline vetorial, com vetores Titan V2
    reais ja computados, so sem chamar a AWS. Qualquer outro valor cai em
    ``"demo"`` por seguranca (nunca afirma "real" sem confirmar o modo
    exato esperado).
    """
    return "real" if embedder in ("bedrock", "cached") else "demo"


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


class SearchResultOut(BaseModel):
    """Um chunk casado — resultado plano, sem agrupamento por familia (issue #78)."""

    family_id: str
    document_version: str
    excerpt: str
    score: float
    localizador: str | None  # extracted_text_locator da DocumentVersion; None se ausente
    document_type: str
    document_id: str
    processo_numero: str | None
    version_date: str
    chunk_id: str  # id estavel do chunk no indice do ai (issue #96)
    chunk_index: int  # indice real do chunk no documento (0-based, issue #96)


class SearchEnvelope(BaseModel):
    request_id: str
    data_mode: str
    corpus_version: str
    model_version: str
    ranking_version: str
    results: list[SearchResultOut]
    total: int
    next_cursor: str | None = None
    stale_corpus: bool = False


# ---------------------------------------------------------------------------
# Corpus version helpers (issue #81)
# ---------------------------------------------------------------------------

def _latest_corpus_version(session: Session) -> str:
    """Retorna o corpus_version mais recente presente no catalogo.

    "Mais recente" e o da ultima ingestao: o ``corpus_version`` da linha
    de ``DocumentVersion`` com o maior ``ingested_at`` (issue #97). Nao
    usa ``max(corpus_version)``: com ``corpus_version`` = hash do
    manifesto (#68), a ordem lexicografica nao tem relacao com a ordem
    temporal. Se a tabela estiver vazia (catalogo sem documentos),
    retorna o fallback de ``Settings.default_corpus_version``.
    """
    result = session.scalar(
        select(DocumentVersion.corpus_version)
        .order_by(DocumentVersion.ingested_at.desc())
        .limit(1)
    )
    return result or get_settings().default_corpus_version


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
        all_results, _ = _build_chunk_results(raw_hits, session)
        total = len(all_results)
        page_results = all_results[offset : offset + limit]

        next_offset = offset + limit
        next_cursor = _encode_cursor(request_id, next_offset) if next_offset < total else None

        stale_corpus = execution.corpus_version != _latest_corpus_version(session)

        return SearchEnvelope(
            request_id=execution.request_id,
            data_mode=execution.data_mode,
            corpus_version=execution.corpus_version,
            model_version=execution.model_version,
            ranking_version=execution.ranking_version,
            results=page_results,
            total=total,
            next_cursor=next_cursor,
            stale_corpus=stale_corpus,
        )

    # --- Primeira chamada: executa busca no ai, persiste, devolve primeiro lote ---
    ai_response = ai_client.search(payload.query, top_k=payload.top_k)
    all_results, corpus_version = _build_chunk_results(ai_response.hits, session)
    total = len(all_results)
    page_results = all_results[:limit]

    request_id = str(uuid.uuid4())
    next_offset = limit
    next_cursor = _encode_cursor(request_id, next_offset) if next_offset < total else None

    envelope = SearchEnvelope(
        request_id=request_id,
        data_mode=_data_mode_for(get_settings().embedder),
        corpus_version=corpus_version,
        model_version=ai_response.model_version,
        ranking_version=RANKING_VERSION,
        results=page_results,
        total=total,
        next_cursor=next_cursor,
        stale_corpus=False,
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

    ``raw_hits`` sao os hits CRUS devolvidos pelo ai, antes de qualquer
    transformacao - e esse valor, nao ``envelope.results`` (que pode ser
    um slice da primeira pagina), que ``app/replay.py::replay_search``
    reusa para reexecutar a busca offline.

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
# Construcao dos resultados por chunk (issue #78 — substitui _group_by_family)
# ---------------------------------------------------------------------------

def _build_chunk_results(
    hits: list[AiSearchHit], session: Session
) -> tuple[list[SearchResultOut], str]:
    """Converte hits crus do ai em resultados planos, um por chunk.

    Cada hit vira um ``SearchResultOut`` independente — sem agrupamento
    por ``family_id``. O mesmo hit devolvido duas vezes pelo ai aparece
    duas vezes na lista resultante.

    Ordenacao final: ``(-score, document_version, chunk_index)``
    — score decrescente, desempate lexicografico por ``document_version``,
    desempate final pelo indice real do chunk no documento (``chunk_index``,
    vindo do ai - issue #96). A ordenacao e estavel: hits com a chave
    inteira igual (o mesmo chunk devolvido duas vezes) mantem a ordem do ai.

    ``corpus_version`` vem da primeira ``DocumentVersion`` encontrada; cai
    para ``Settings.default_corpus_version`` quando nenhum hit resolve para
    uma versao conhecida.
    """
    results: list[SearchResultOut] = []
    corpus_version: str | None = None

    for hit in hits:
        version = session.get(DocumentVersion, hit.document_version)
        if version is None:
            # O ai devolveu um document_version ausente do catalogo — pula
            # em vez de quebrar a busca inteira.
            continue

        if corpus_version is None:
            corpus_version = version.corpus_version

        results.append(
            SearchResultOut(
                family_id=hit.family_id,
                document_version=hit.document_version,
                excerpt=hit.excerpt,
                score=hit.score,
                localizador=version.extracted_text_locator or None,
                document_type=version.document_type,
                document_id=version.document_id,
                processo_numero=version.processo_numero,
                version_date=version.version_date,
                chunk_id=hit.chunk_id,
                chunk_index=hit.chunk_index,
            )
        )

    # Ordenacao deterministica: score desc, depois document_version asc, depois chunk_index asc
    results.sort(key=lambda r: (-r.score, r.document_version, r.chunk_index))

    if corpus_version is None:
        corpus_version = get_settings().default_corpus_version

    return results, corpus_version


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
