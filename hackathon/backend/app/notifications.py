"""Geracao de notificacoes + digest de e-mail (TB1 Ticket 8, issue #24).

``run_notifications`` roda a partir de ``app/routes/ingestions.py::run_ingestion``,
sempre (nao e opcional como ``relations`` foi para os Tickets 2-4) -
zero usuarios com escopo escolhido e um no-op seguro, ver
test_notifications_ingestion.py. Gatilho = qualquer documento do corpus
ingerido (familia nova ou versao nova), nunca filtrado por
"acompanhamento" (decisao fechada em u3-frequency.md).

Para cada usuario com ``notification_scope_preference`` ja escolhida,
para cada documento do corpus:

- Se ja existe ``notification(user_id, document_version_id)``: nao cria
  linha nova, registra ``notification_suppressed`` (cobre reindexar o
  mesmo ``corpus_version``).
- Senao: monta ``reasons`` (``novo_documento`` sempre; no escopo
  ``ampla``, mais um item por aresta ``confirmed`` de
  ``document_relations`` tocando a familia - exceto
  ``pertence_ao_processo``, que e vinculo estrutural de processo, nao
  um "correlato" no sentido de u3-frequency.md), cria a notificacao,
  registra ``notification_generated`` e ``notification_delivered_home``
  (a home mostra cada notificacao imediatamente, sem passo de entrega
  separado nesta fase demo).

Ao fim do loop de um usuario, se pelo menos uma notificacao foi
*gerada* (nao suprimida) nesse job, monta um digest de e-mail via
``Mailer`` (app/mailer.py) - um por ``(user_id, ingestion_job_id)``.
"""

import json

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.fixtures.loader import FixtureCorpus, FixtureDocumentVersion
from app.mailer import PreviewMailer
from app.models import (
    DocumentRelation,
    DocumentVersion,
    Notification,
    NotificationEvent,
    NotificationScopePreference,
)

# Tipos de aresta tratados como "correlato" no escopo ampla
# (u3-frequency.md: "familias/processos ligados por aresta referencia,
# similar_a, e os tipos finos revoga/altera/responde_a/regula").
# pertence_ao_processo fica de fora - e o vinculo estrutural
# peca->processo, nao um correlato.
_CORRELATO_TYPES = {"referencia", "similar_a", "revoga", "altera", "responde_a", "regula"}


def run_notifications(
    corpus: FixtureCorpus, *, session: Session, ingestion_job_id: str
) -> None:
    """Gera notificacoes + digests de e-mail para o corpus recem-ingerido.

    So processa usuarios que ja escolheram ``notification_scope``
    (ver app/routes/notifications.py::set_notification_scope) - nenhuma
    notificacao e gerada para quem ainda nao escolheu (sem padrao,
    decisao fechada em u3-frequency.md).
    """
    preferences = session.scalars(select(NotificationScopePreference)).all()

    for preference in preferences:
        generated_ids: list[int] = []
        for doc in corpus.documents:
            notification, was_generated = _notify_user_for_document(
                session,
                user_id=preference.user_id,
                scope=preference.scope,
                doc=doc,
                ingestion_job_id=ingestion_job_id,
            )
            if was_generated:
                generated_ids.append(notification.id)

        if generated_ids:
            _send_digest(
                session,
                user_id=preference.user_id,
                ingestion_job_id=ingestion_job_id,
                notification_ids=generated_ids,
            )


def _notify_user_for_document(
    session: Session,
    *,
    user_id: str,
    scope: str,
    doc: FixtureDocumentVersion,
    ingestion_job_id: str,
) -> tuple[Notification, bool]:
    existing = session.scalar(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.document_version_id == doc.document_version,
        )
    )
    if existing is not None:
        _record_event(
            session,
            event_type="notification_suppressed",
            user_id=user_id,
            document_version_id=doc.document_version,
            notification_id=existing.id,
            payload={"reason": "duplicate", "existing_notification_id": existing.id},
        )
        return existing, False

    reasons: list[dict[str, str]] = [{"type": "novo_documento"}]
    if scope == "ampla":
        reasons.extend(_correlato_reasons(session, doc.family_id))

    notification = Notification(
        user_id=user_id,
        document_version_id=doc.document_version,
        family_id=doc.family_id,
        scope_effective=scope,
        reasons_json=json.dumps(reasons),
        ingestion_job_id=ingestion_job_id,
    )
    session.add(notification)
    session.flush()  # precisa do id gerado (autoincrement) para eventos/digest.

    _record_event(
        session,
        event_type="notification_generated",
        user_id=user_id,
        document_version_id=doc.document_version,
        notification_id=notification.id,
        payload={"scope_effective": scope, "reasons": reasons},
    )
    _record_event(
        session,
        event_type="notification_delivered_home",
        user_id=user_id,
        document_version_id=doc.document_version,
        notification_id=notification.id,
    )
    return notification, True


def _correlato_reasons(session: Session, family_id: str) -> list[dict[str, str]]:
    edges = session.scalars(
        select(DocumentRelation).where(
            DocumentRelation.status == "confirmed",
            DocumentRelation.type.in_(_CORRELATO_TYPES),
            or_(
                DocumentRelation.source_id == family_id,
                DocumentRelation.target_id == family_id,
            ),
        )
    ).all()

    reasons: list[dict[str, str]] = []
    for edge in edges:
        if edge.source_id == family_id:
            neighbor_id, neighbor_kind = edge.target_id, edge.target_kind
        else:
            neighbor_id, neighbor_kind = edge.source_id, edge.source_kind
        reasons.append(
            {
                "type": "correlato",
                "relation_type": edge.type,
                "neighbor_family_id": neighbor_id,
                "neighbor_kind": neighbor_kind,
            }
        )
    return reasons


def _send_digest(
    session: Session, *, user_id: str, ingestion_job_id: str, notification_ids: list[int]
) -> None:
    email_id = f"{user_id}:{ingestion_job_id}"
    notifications = session.scalars(
        select(Notification).where(Notification.id.in_(notification_ids))
    ).all()
    body = _render_digest_body(session, notifications)

    mailer = PreviewMailer(session)
    report = mailer.send(
        email_id,
        user_id,
        f"CapiWatt Lens - {len(notifications)} novo(s) documento(s)",
        body,
        user_id=user_id,
        ingestion_job_id=ingestion_job_id,
        notification_ids=notification_ids,
    )

    _record_event(
        session,
        event_type="email_digest_generated",
        user_id=user_id,
        email_id=email_id,
        payload={"ingestion_job_id": ingestion_job_id, "notification_count": len(notifications)},
    )
    _record_event(
        session,
        event_type="notification_delivered_email",
        user_id=user_id,
        email_id=email_id,
        payload={"adapter": report.adapter, "status": report.status},
    )


def _render_digest_body(session: Session, notifications: list[Notification]) -> str:
    lines = [f"Você tem {len(notifications)} novo(s) documento(s):"]
    for notification in notifications:
        version = session.get(DocumentVersion, notification.document_version_id)
        if version is not None:
            lines.append(f"- {version.document_type} {version.document_id}")
        else:
            # Nao deveria acontecer com o fluxo normal (a notificacao so
            # existe para um document_version recem-ingerido), mas evita
            # quebrar o digest inteiro por uma linha so.
            lines.append(f"- {notification.family_id} (versão {notification.document_version_id})")
    return "\n".join(lines)


def _record_event(
    session: Session,
    *,
    event_type: str,
    user_id: str,
    document_version_id: str | None = None,
    notification_id: int | None = None,
    email_id: str | None = None,
    payload: dict | None = None,
) -> None:
    session.add(
        NotificationEvent(
            event_type=event_type,
            user_id=user_id,
            document_version_id=document_version_id,
            notification_id=notification_id,
            email_id=email_id,
            payload_json=json.dumps(payload) if payload is not None else None,
        )
    )
