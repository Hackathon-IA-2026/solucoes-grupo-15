"""Rotas publicas de notificacoes (TB1 Ticket 8, issue #24).

``PUT``/``GET /v1/users/{user_id}/notification-scope`` implementam a
escolha obrigatoria de escopo (``estrita``/``ampla``, sem padrao -
decisao fechada em u3-frequency.md). ``user_id`` e so uma string
recebida via path param, sem autenticacao nenhuma (fora de escopo de
toda a spec #16); o conjunto de usuarios demo (``carolina``/``equipe``)
e uma convencao so do frontend (ver
hackathon/frontend/src/api/notifications.ts), nao validada aqui.

``GET /v1/users/{user_id}/notifications`` lista as notificacoes de um
usuario, mais recente primeiro, enriquecidas com dado de exibicao do
catalogo (``document_type``/``document_id`` da versao) para o
frontend montar o link (``/documents/{family_id}``) e um texto
legivel.

``POST /v1/notifications/{notification_id}/opened`` registra
``notification_opened`` quando o usuario clica no link de uma
notificacao na home (``origin: "home"`` - abertura de e-mail com pixel
esta fora de escopo, i6-telemetry.md).

``GET /v1/notification-events`` e ``GET /v1/users/{user_id}/email-digests``
existem para conferencia/auditoria manual: confirmar "sem duplicacao"
por consulta (nenhum ``(user_id, document_version_id)`` com dois
``notification_generated``) e ver a previa de cada digest de e-mail na
pagina inicial.
"""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.models import (
    DocumentVersion,
    EmailDigest,
    Notification,
    NotificationEvent,
    NotificationScopePreference,
)

router = APIRouter(prefix="/v1", tags=["notifications"])

Scope = Literal["estrita", "ampla"]


class NotificationScopeIn(BaseModel):
    scope: Scope


class NotificationScopeOut(BaseModel):
    scope: Scope | None


class NotificationOut(BaseModel):
    id: int
    user_id: str
    document_version_id: str
    family_id: str
    document_type: str | None
    document_id: str | None
    scope_effective: str
    reasons: list[dict]
    ingestion_job_id: str
    created_at: str


class NotificationOpenedOut(BaseModel):
    notification_id: int
    opened: bool = True


class EmailDigestOut(BaseModel):
    email_id: str
    user_id: str
    ingestion_job_id: str
    notification_ids: list[int]
    rendered_body: str
    created_at: str


class NotificationEventOut(BaseModel):
    id: int
    event_type: str
    user_id: str
    document_version_id: str | None
    notification_id: int | None
    email_id: str | None
    payload: dict | None
    created_at: str


@router.put("/users/{user_id}/notification-scope", response_model=NotificationScopeOut)
def set_notification_scope(
    user_id: str, payload: NotificationScopeIn, session: Session = Depends(get_db_session)
) -> NotificationScopeOut:
    preference = session.get(NotificationScopePreference, user_id)
    if preference is None:
        preference = NotificationScopePreference(user_id=user_id, scope=payload.scope)
        session.add(preference)
    else:
        preference.scope = payload.scope
    session.flush()
    return NotificationScopeOut(scope=preference.scope)


@router.get("/users/{user_id}/notification-scope", response_model=NotificationScopeOut)
def get_notification_scope(
    user_id: str, session: Session = Depends(get_db_session)
) -> NotificationScopeOut:
    preference = session.get(NotificationScopePreference, user_id)
    return NotificationScopeOut(scope=preference.scope if preference is not None else None)


@router.get("/users/{user_id}/notifications", response_model=list[NotificationOut])
def list_notifications(
    user_id: str, session: Session = Depends(get_db_session)
) -> list[NotificationOut]:
    rows = session.scalars(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.id.desc())
    ).all()

    out: list[NotificationOut] = []
    for row in rows:
        version = session.get(DocumentVersion, row.document_version_id)
        out.append(
            NotificationOut(
                id=row.id,
                user_id=row.user_id,
                document_version_id=row.document_version_id,
                family_id=row.family_id,
                document_type=version.document_type if version is not None else None,
                document_id=version.document_id if version is not None else None,
                scope_effective=row.scope_effective,
                reasons=json.loads(row.reasons_json),
                ingestion_job_id=row.ingestion_job_id,
                created_at=row.created_at.isoformat(),
            )
        )
    return out


@router.post("/notifications/{notification_id}/opened", response_model=NotificationOpenedOut)
def mark_notification_opened(
    notification_id: int, session: Session = Depends(get_db_session)
) -> NotificationOpenedOut:
    notification = session.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")

    session.add(
        NotificationEvent(
            event_type="notification_opened",
            user_id=notification.user_id,
            document_version_id=notification.document_version_id,
            notification_id=notification.id,
            payload_json=json.dumps({"origin": "home"}),
        )
    )
    session.flush()
    return NotificationOpenedOut(notification_id=notification_id)


@router.get("/users/{user_id}/email-digests", response_model=list[EmailDigestOut])
def list_email_digests(
    user_id: str, session: Session = Depends(get_db_session)
) -> list[EmailDigestOut]:
    rows = session.scalars(
        select(EmailDigest)
        .where(EmailDigest.user_id == user_id)
        .order_by(EmailDigest.created_at.desc(), EmailDigest.email_id.desc())
    ).all()
    return [
        EmailDigestOut(
            email_id=row.email_id,
            user_id=row.user_id,
            ingestion_job_id=row.ingestion_job_id,
            notification_ids=json.loads(row.notification_ids_json),
            rendered_body=row.rendered_body,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.get("/notification-events", response_model=list[NotificationEventOut])
def list_notification_events(
    user_id: str | None = None,
    document_version_id: str | None = None,
    session: Session = Depends(get_db_session),
) -> list[NotificationEventOut]:
    query = select(NotificationEvent).order_by(NotificationEvent.id.desc())
    if user_id is not None:
        query = query.where(NotificationEvent.user_id == user_id)
    if document_version_id is not None:
        query = query.where(NotificationEvent.document_version_id == document_version_id)

    rows = session.scalars(query).all()
    return [
        NotificationEventOut(
            id=row.id,
            event_type=row.event_type,
            user_id=row.user_id,
            document_version_id=row.document_version_id,
            notification_id=row.notification_id,
            email_id=row.email_id,
            payload=json.loads(row.payload_json) if row.payload_json is not None else None,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
