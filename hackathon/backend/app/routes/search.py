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

Ticket 9 (issue #25, reprodutibilidade) acrescenta a persistencia de
``SearchExecution`` (app/models.py) a cada chamada: alem do envelope
final, grava os hits CRUS devolvidos por ``ai_client.search`` (antes
do agrupamento por familia) - e o "vetor da consulta preservado" desta
fase demo, que ``app/replay.py::replay_search`` usa para reexecutar a
busca offline, sem chamar o ai de novo (ver i7-reproducibility).
"""

import json
import uuid

from fastapi import APIRouter, Depends
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


class SearchRequestIn(BaseModel):
    query: str
    top_k: int | None = None


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


@router.post("/search", response_model=SearchEnvelope)
def search(
    payload: SearchRequestIn,
    ai_client: AiClient = Depends(get_ai_client),
    session: Session = Depends(get_db_session),
) -> SearchEnvelope:
    ai_response = ai_client.search(payload.query, top_k=payload.top_k)
    results, corpus_version = _group_by_family(ai_response.hits, session)

    envelope = SearchEnvelope(
        request_id=str(uuid.uuid4()),
        data_mode="demo",
        corpus_version=corpus_version,
        model_version=ai_response.model_version,
        ranking_version=RANKING_VERSION,
        results=results,
    )

    _persist_search_execution(
        envelope, query=payload.query, raw_hits=ai_response.hits, session=session
    )

    return envelope


def _persist_search_execution(
    envelope: SearchEnvelope,
    *,
    query: str,
    raw_hits: list[AiSearchHit],
    session: Session,
) -> None:
    """Grava o registro de execucao desta busca (Ticket 9, issue #25).

    ``raw_hits`` sao os hits CRUS devolvidos pelo ai, antes do
    agrupamento por familia - e esse valor, nao ``envelope.results``,
    que ``app/replay.py::replay_search`` reusa para reexecutar a busca
    offline (ver docstring do modulo).
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
