"""Contrato de geracao de notificacoes + digest de e-mail a partir da
ingestao (TB1 Ticket 8, issue #24, seams 2 e 3).

Popula preferencias de escopo de 2 usuarios (um estrita, um ampla)
antes de chamar POST /v1/ingestions e confirma: uma notificacao gerada
por versao para cada usuario; no escopo ampla, ``reasons`` inclui os
correlatos esperados (fixture de relacoes do Ticket 5, ja no repo);
reingestao do mesmo corpus nao duplica ``notification`` (uniq
constraint) e gera ``notification_suppressed`` com motivo; eventos
``notification_generated``/``notification_delivered_home`` batem em
quantidade com as notificacoes criadas; um ``email_digest`` por
``(user_id, ingestion_job_id)`` existe com ``rendered_body`` nao vazio
e e idempotente por ``email_id``; eventos
``email_digest_generated``/``notification_delivered_email`` gravados.

Roda contra um Postgres real de teste (container Docker, ver
tests/conftest.py) e isola o ai via dependency override (fake
deterministico), mesmo padrao dos demais testes de ingestao.
"""

import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import IndexDocumentPayload, IndexReport, get_ai_client
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.fixtures.loader import load_demo_corpus
from app.mailer import PreviewMailer
from app.main import create_app
from app.models import EmailDigest, Notification, NotificationEvent


class _FakeAiClient:
    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        return [
            IndexReport(
                document_version=doc.document_version,
                extracted_text_locator=f"/data/documents/{doc.document_version}/extracted.txt",
                chunks_indexed=1,
                model_version="fixture-demo",
            )
            for doc in documents
        ]


def _client(database_url: str) -> tuple[TestClient, sessionmaker[Session]]:
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)

    def _override_session():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeAiClient()
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app), session_factory


def _set_scope(client: TestClient, user_id: str, scope: str) -> None:
    response = client.put(f"/v1/users/{user_id}/notification-scope", json={"scope": scope})
    assert response.status_code == 200


def test_ingestion_generates_one_notification_per_version_per_user_with_scope(
    database_url: str,
) -> None:
    client, session_factory = _client(database_url)
    corpus = load_demo_corpus()
    _set_scope(client, "carolina", "estrita")
    _set_scope(client, "equipe", "ampla")

    response = client.post("/v1/ingestions")
    assert response.status_code == 200

    with session_factory() as session:
        carolina_notifications = session.scalars(
            select(Notification).where(Notification.user_id == "carolina")
        ).all()
        equipe_notifications = session.scalars(
            select(Notification).where(Notification.user_id == "equipe")
        ).all()

    assert len(carolina_notifications) == len(corpus.documents)
    assert len(equipe_notifications) == len(corpus.documents)
    assert {n.document_version_id for n in carolina_notifications} == {
        doc.document_version for doc in corpus.documents
    }
    assert all(n.scope_effective == "estrita" for n in carolina_notifications)
    assert all(n.scope_effective == "ampla" for n in equipe_notifications)


def test_user_without_scope_choice_gets_no_notifications(database_url: str) -> None:
    client, session_factory = _client(database_url)
    _set_scope(client, "carolina", "estrita")
    # "equipe" nunca escolheu escopo.

    client.post("/v1/ingestions")

    with session_factory() as session:
        equipe_notifications = session.scalars(
            select(Notification).where(Notification.user_id == "equipe")
        ).all()

    assert equipe_notifications == []


def test_estrita_scope_reasons_only_have_novo_documento(database_url: str) -> None:
    client, session_factory = _client(database_url)
    _set_scope(client, "carolina", "estrita")

    client.post("/v1/ingestions")

    with session_factory() as session:
        notifications = session.scalars(
            select(Notification).where(Notification.user_id == "carolina")
        ).all()

    for notification in notifications:
        reasons = _load_reasons(notification)
        assert reasons == [{"type": "novo_documento"}]


def test_ampla_scope_includes_confirmed_correlatos_for_decisao_family(
    database_url: str,
) -> None:
    client, session_factory = _client(database_url)
    _set_scope(client, "equipe", "ampla")

    client.post("/v1/ingestions")

    with session_factory() as session:
        notification = session.scalar(
            select(Notification).where(
                Notification.user_id == "equipe",
                Notification.document_version_id == "docver-decisao-0007-v1",
            )
        )

    assert notification is not None
    reasons = _load_reasons(notification)
    assert reasons[0] == {"type": "novo_documento"}

    correlatos = reasons[1:]
    assert len(correlatos) == 2
    relation_types = {c["relation_type"] for c in correlatos}
    assert relation_types == {"regula", "referencia"}
    neighbor_ids = {c["neighbor_family_id"] for c in correlatos}
    assert neighbor_ids == {"fam-norma-1000", "fam-auto-0007"}
    # pertence_ao_processo e vinculo estrutural, nao correlato (u3-frequency.md).
    assert all(c["relation_type"] != "pertence_ao_processo" for c in correlatos)


def test_reingesting_same_corpus_does_not_duplicate_notifications(database_url: str) -> None:
    client, session_factory = _client(database_url)
    corpus = load_demo_corpus()
    _set_scope(client, "carolina", "estrita")

    client.post("/v1/ingestions")
    client.post("/v1/ingestions")

    with session_factory() as session:
        notifications = session.scalars(
            select(Notification).where(Notification.user_id == "carolina")
        ).all()
        suppressed_events = session.scalars(
            select(NotificationEvent).where(
                NotificationEvent.event_type == "notification_suppressed",
                NotificationEvent.user_id == "carolina",
            )
        ).all()

    assert len(notifications) == len(corpus.documents)
    assert len(suppressed_events) == len(corpus.documents)
    for event in suppressed_events:
        payload = _load_payload(event)
        assert payload["reason"] == "duplicate"
        assert payload["existing_notification_id"] is not None


def test_generated_and_delivered_home_events_match_notification_count(
    database_url: str,
) -> None:
    client, session_factory = _client(database_url)
    corpus = load_demo_corpus()
    _set_scope(client, "carolina", "estrita")

    client.post("/v1/ingestions")

    with session_factory() as session:
        generated_events = session.scalars(
            select(NotificationEvent).where(
                NotificationEvent.event_type == "notification_generated",
                NotificationEvent.user_id == "carolina",
            )
        ).all()
        delivered_home_events = session.scalars(
            select(NotificationEvent).where(
                NotificationEvent.event_type == "notification_delivered_home",
                NotificationEvent.user_id == "carolina",
            )
        ).all()

    assert len(generated_events) == len(corpus.documents)
    assert len(delivered_home_events) == len(corpus.documents)


def test_email_digest_created_per_user_and_job_with_rendered_body(database_url: str) -> None:
    client, session_factory = _client(database_url)
    _set_scope(client, "carolina", "estrita")

    response = client.post("/v1/ingestions")
    ingestion_job_id = response.json()["ingestion_job_id"]

    with session_factory() as session:
        digest = session.get(EmailDigest, f"carolina:{ingestion_job_id}")
        digest_generated_events = session.scalars(
            select(NotificationEvent).where(
                NotificationEvent.event_type == "email_digest_generated",
                NotificationEvent.user_id == "carolina",
            )
        ).all()
        delivered_email_events = session.scalars(
            select(NotificationEvent).where(
                NotificationEvent.event_type == "notification_delivered_email",
                NotificationEvent.user_id == "carolina",
            )
        ).all()

    assert digest is not None
    assert digest.user_id == "carolina"
    assert digest.ingestion_job_id == ingestion_job_id
    assert digest.rendered_body.strip() != ""
    assert len(digest_generated_events) == 1
    assert len(delivered_email_events) == 1
    payload = _load_payload(delivered_email_events[0])
    assert payload["adapter"] == "preview"


def test_no_digest_generated_for_user_whose_notifications_were_all_suppressed(
    database_url: str,
) -> None:
    client, session_factory = _client(database_url)
    _set_scope(client, "carolina", "estrita")

    client.post("/v1/ingestions")
    second = client.post("/v1/ingestions")
    second_job_id = second.json()["ingestion_job_id"]

    with session_factory() as session:
        digest = session.get(EmailDigest, f"carolina:{second_job_id}")

    assert digest is None


def test_mailer_send_is_idempotent_by_email_id(database_url: str) -> None:
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        mailer = PreviewMailer(session)
        first = mailer.send(
            "digest-1",
            "carolina",
            "assunto",
            "corpo original",
            user_id="carolina",
            ingestion_job_id="job-1",
            notification_ids=[1, 2],
        )
        second = mailer.send(
            "digest-1",
            "carolina",
            "assunto",
            "corpo diferente - nao deveria sobrescrever",
            user_id="carolina",
            ingestion_job_id="job-1",
            notification_ids=[1, 2, 3],
        )
        session.commit()

        rows = session.scalars(
            select(EmailDigest).where(EmailDigest.email_id == "digest-1")
        ).all()

    assert first.email_id == second.email_id == "digest-1"
    assert first.status == second.status == "previewed"
    assert len(rows) == 1
    assert rows[0].rendered_body == "corpo original"


def _load_reasons(notification: Notification) -> list[dict]:
    return json.loads(notification.reasons_json)


def _load_payload(event: NotificationEvent) -> dict:
    return json.loads(event.payload_json)
