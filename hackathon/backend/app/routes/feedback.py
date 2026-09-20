"""Rota publica de feedback (👍/👎) sobre resultados de busca (TB1 Ticket 7,
issue #23).

``POST /v1/feedback`` persiste um voto sobre um card de resultado de
busca (ticket 3, issue #19): liga o voto ao ``request_id`` da chamada
de POST /v1/search que produziu o card e ao ``family_id`` avaliado.
``vote`` so aceita ``"up"``/``"down"`` (qualquer outro valor -> 422,
validacao do Pydantic via ``Literal``); nenhum campo de
justificativa/comentario e exigido nem aceito, por decisao explicita
da issue.

``GET /v1/feedback`` lista o feedback registrado, para conferencia
manual - sem paginacao sofisticada, so um ``limit`` opcional (mais
recente primeiro) e filtros opcionais por ``request_id``/``family_id``
via query params.
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
    family_id: str
    vote: Literal["up", "down"]


class FeedbackOut(BaseModel):
    id: int
    request_id: str
    family_id: str
    vote: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


@router.post("/feedback", response_model=FeedbackOut)
def create_feedback(
    payload: FeedbackIn, session: Session = Depends(get_db_session)
) -> Feedback:
    feedback = Feedback(
        request_id=payload.request_id,
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
    family_id: str | None = None,
    limit: int | None = None,
    session: Session = Depends(get_db_session),
) -> list[Feedback]:
    query = select(Feedback).order_by(Feedback.id.desc())
    if request_id is not None:
        query = query.where(Feedback.request_id == request_id)
    if family_id is not None:
        query = query.where(Feedback.family_id == family_id)
    if limit is not None:
        query = query.limit(limit)

    return list(session.scalars(query).all())
