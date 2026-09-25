"""Operacoes administrativas do ambiente demonstrativo (issue #38).

O reset remove somente dados produzidos pelas interacoes dos visitantes.
O corpus documental, suas versoes, relacoes e arquivos extraidos permanecem
intactos para que a demonstracao possa recomecar sem nova infraestrutura.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.models import (
    EmailDigest,
    Feedback,
    Notification,
    NotificationEvent,
    NotificationScopePreference,
    SearchExecution,
)

router = APIRouter(prefix="/v1/demo", tags=["demo"])


class DemoResetOut(BaseModel):
    deleted: dict[str, int]


@router.post("/reset", response_model=DemoResetOut)
def reset_demo(session: Session = Depends(get_db_session)) -> DemoResetOut:
    models = [
        ("notification_events", NotificationEvent),
        ("email_digests", EmailDigest),
        ("notifications", Notification),
        ("notification_scope_preferences", NotificationScopePreference),
        ("feedback", Feedback),
        ("search_executions", SearchExecution),
    ]
    deleted = {
        name: int(session.execute(delete(model)).rowcount or 0)
        for name, model in models
    }
    session.flush()
    return DemoResetOut(deleted=deleted)
