"""Rota publica de feedback (👍/👎) sobre resultados de busca (TB1 Ticket 7,
issue #23; chave de chunk issue #82).

``POST /v1/feedback`` persiste um voto sobre um card de resultado de
busca. Desde a issue #82 (resultados por chunk, issue #78), o payload
primario identifica o chunk exato: ``document_version`` + ``chunk_index``
sao obrigatorios; ``family_id`` e opcional (pode ser omitido).
Desde a issue #96, ``chunk_index`` e o indice real do chunk no documento
(o mesmo devolvido em cada resultado de ``POST /v1/search``, vindo do
``chunk_id`` do indice do ai), nao a posicao do card na lista - o voto
aponta para um chunk estavel entre consultas. O campo
``request_id`` permanece obrigatorio para ligar o voto a execucao de
busca que gerou o resultado.

``vote`` so aceita ``"up"``/``"down"`` (qualquer outro valor -> 422,
validacao do Pydantic via ``Literal``); nenhum campo de
justificativa/comentario e exigido nem aceito, por decisao explicita
da issue.

``GET /v1/feedback`` lista o feedback registrado, para conferencia
manual - sem paginacao sofisticada, so um ``limit`` opcional (mais
recente primeiro) e filtros opcionais por ``request_id``,
``document_version``, ``chunk_index`` e ``family_id`` via query params.
"""

import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.models import Feedback

router = APIRouter(prefix="/v1", tags=["feedback"])


class FeedbackIn(BaseModel):
    request_id: str
    document_version: str           # novo obrigatorio (issue #82)
    chunk_index: int                 # novo obrigatorio (issue #82)
    family_id: str | None = None     # agora opcional; preserva compatibilidade legada
    vote: Literal["up", "down"]


class FeedbackOut(BaseModel):
    id: int
    request_id: str
    document_version: str | None
    chunk_index: int | None
    family_id: str | None
    vote: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


@router.post("/feedback", response_model=FeedbackOut)
def create_feedback(
    payload: FeedbackIn, session: Session = Depends(get_db_session)
) -> Feedback:
    feedback = Feedback(
        request_id=payload.request_id,
        document_version=payload.document_version,
        chunk_index=payload.chunk_index,
        family_id=payload.family_id,
        vote=payload.vote,
    )
    session.add(feedback)
    session.flush()
    session.refresh(feedback)
    return feedback


@router.get("/feedback", response_model=list[FeedbackOut])
def list_feedback(
    request_id: str | None = None,
    document_version: str | None = None,
    chunk_index: int | None = None,
    family_id: str | None = None,
    limit: int | None = None,
    session: Session = Depends(get_db_session),
) -> list[Feedback]:
    query = select(Feedback).order_by(Feedback.id.desc())
    if request_id is not None:
        query = query.where(Feedback.request_id == request_id)
    if document_version is not None:
        query = query.where(Feedback.document_version == document_version)
    if chunk_index is not None:
        query = query.where(Feedback.chunk_index == chunk_index)
    if family_id is not None:
        query = query.where(Feedback.family_id == family_id)
    if limit is not None:
        query = query.limit(limit)

    return list(session.scalars(query).all())
