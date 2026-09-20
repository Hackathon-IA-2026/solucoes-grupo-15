"""Modelos ORM do catalogo documental.

``document_family``/``document_version`` vem do Ticket 2 (issue #18):
exatamente como o corpus de fixtures demo declara (ver
app/fixtures/demo_corpus.json). Nenhuma regra de classificacao ou de
chave explicita e aplicada aqui.

``document_relations`` (Ticket 5, issue #21) guarda as arestas do
grafo de relacoes (peca->processo, familia->familia, norma->peca)
declaradas literalmente pela fixture de relacoes
(app/fixtures/demo_relations.json) - nenhum reconhecedor de padrao
textual roda aqui. Nesta issue toda aresta nasce ``origin="explicit"``,
``status="confirmed"``; sugestao de similaridade/fusao (``score``,
``decided_by``, ``decided_at``) fica para o Ticket opcional #22, fora
de escopo. O no ``processo`` nao ganha tabela propria nesta issue - seu
``id`` e o ``processo_numero`` cru ja gravado em ``DocumentVersion``
(ver ``target_id``/``source_id`` com ``*_kind == "processo"`` em
``document_relations``).
"""

import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DocumentFamily(Base):
    """Identidade logica de uma peca documental (d4-data-dictionary).

    Nenhum campo alem da PK e exigido por esta issue.
    """

    __tablename__ = "document_family"

    family_id: Mapped[str] = mapped_column(String, primary_key=True)

    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="family")


class DocumentVersion(Base):
    """Instancia concreta de uma familia (uma versao/checksum).

    ``version_date``/``version_date_source`` e ``document_type`` vem
    exatamente como a fixture declara - nenhuma regra de classificacao
    ou de chave explicita e aplicada aqui. ``processo_numero`` e o dado
    bruto do processo SEI ao qual a peca pertence, se houver; nenhuma
    tabela ``processo`` ou relacao e criada nesta issue (Ticket 5,
    issue #21). ``document_id`` (Ticket 4, issue #20) e o identificador
    cru do documento na fixture (ex. "auto-0007", compartilhado entre
    as versoes da mesma familia) - usado so como identificador de
    exibicao na pagina de familia, sem nenhuma regra de formatacao por
    tipo documental (isso pertence as issues #10-#14).
    """

    __tablename__ = "document_version"

    document_version: Mapped[str] = mapped_column(String, primary_key=True)
    family_id: Mapped[str] = mapped_column(
        ForeignKey("document_family.family_id"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(String, nullable=False)
    version_date: Mapped[str] = mapped_column(String, nullable=False)
    version_date_source: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    processo_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_text_locator: Mapped[str] = mapped_column(String, nullable=False)
    corpus_version: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)

    family: Mapped["DocumentFamily"] = relationship(back_populates="versions")


class DocumentRelation(Base):
    """Uma aresta do grafo de relacoes (Ticket 5, issue #21).

    Chave natural unica ``(source_id, source_kind, target_id,
    target_kind, type)`` - reingerir a fixture de relacoes faz upsert
    por essa chave, nunca duplica linha (ver
    app/routes/ingestions.py::run_relations_ingestion). ``source_kind``/
    ``target_kind`` sao ``"family"`` ou ``"processo"``; ``type`` e um
    dos sete do vocabulario fechado em d14-data-operations-modeling
    (``pertence_ao_processo``, ``referencia``, ``revoga``, ``altera``,
    ``responde_a``, ``regula``, ``similar_a`` - este ultimo nao usado
    nesta issue). ``evidence_document_version``/``evidence_locator``
    ficam nulos quando a fixture nao declara evidencia (ex.:
    ``pertence_ao_processo``, que vem do metadado ``processo_numero``,
    nao de um trecho de texto).
    """

    __tablename__ = "document_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "source_kind",
            "target_id",
            "target_kind",
            "type",
            name="uq_document_relations_natural_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    target_kind: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    origin: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    evidence_document_version: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_locator: Mapped[str | None] = mapped_column(String, nullable=True)


class Feedback(Base):
    """Um voto 👍/👎 num resultado de busca (Ticket 7, issue #23).

    Liga o voto ao ``request_id`` da chamada de POST /v1/search que
    produziu o card avaliado e ao ``family_id`` avaliado - nenhuma
    chave estrangeira e declarada para nenhum dos dois (``request_id``
    nao e persistido em nenhuma tabela; um ``family_id`` poderia em
    tese ja ter saido do catalogo). Nenhum campo de
    justificativa/comentario existe aqui, por decisao explicita da
    issue. ``vote`` e validado como ``"up"``/``"down"`` na camada da
    rota (Pydantic), nao aqui.
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String, nullable=False)
    family_id: Mapped[str] = mapped_column(String, nullable=False)
    vote: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NotificationScopePreference(Base):
    """Escolha de escopo de notificacao de um usuario (TB1 Ticket 8, issue #24).

    ``user_id`` e uma string simples de usuario demo hardcoded
    (``["carolina", "equipe"]`` no frontend, ver src/api/notifications.ts)
    - nao existe autenticacao/sessao neste scaffold (fora de escopo de
    toda a spec #16); qualquer string e aceita aqui. Sem valor padrao
    para ``scope`` (decisao fechada em u3-frequency.md): enquanto nao
    existir linha para um ``user_id``, nenhuma notificacao e gerada
    para ele (ver app/notifications.py::run_notifications).
    """

    __tablename__ = "notification_scope_preference"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Notification(Base):
    """Uma notificacao gerada para um usuario (TB1 Ticket 8, issue #24).

    Restricao unica ``(user_id, document_version_id)`` (i9-integration):
    dedup de notificacao - reingerir o mesmo corpus_version nao cria
    uma segunda linha para o mesmo par, ver
    app/notifications.py::run_notifications, que registra
    ``notification_suppressed`` nesse caso. ``reasons_json`` e uma
    lista JSON serializada (``[{"type": "novo_documento"}]`` sempre; no
    escopo ``ampla``, mais um item ``{"type": "correlato", ...}`` por
    aresta ``confirmed`` de document_relations tocando a familia).
    """

    __tablename__ = "notification"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "document_version_id",
            name="uq_notification_user_document_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    document_version_id: Mapped[str] = mapped_column(String, nullable=False)
    family_id: Mapped[str] = mapped_column(String, nullable=False)
    scope_effective: Mapped[str] = mapped_column(String, nullable=False)
    reasons_json: Mapped[str] = mapped_column(String, nullable=False)
    ingestion_job_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NotificationEvent(Base):
    """Evento do ciclo de vida de notificacao (TB1 Ticket 8, issue #24).

    Vocabulario fechado em i6-telemetry.md: ``notification_generated``,
    ``notification_suppressed``, ``email_digest_generated``,
    ``notification_delivered_home``, ``notification_delivered_email``,
    ``notification_opened``. Nenhuma chave estrangeira para
    ``notification``/``email_digest`` (mesmo padrao de ``Feedback`` -
    simplicidade > integridade referencial nesta fase demo);
    ``payload_json`` guarda campos extras por tipo de evento (ex.
    ``reason`` de supressao, ``adapter``/``status`` de entrega).
    """

    __tablename__ = "notification_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    notification_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EmailDigest(Base):
    """Prevía de digest de e-mail por (usuario, job de ingestao) (TB1
    Ticket 8, issue #24).

    Gravada pelo adapter ``PreviewMailer`` (app/mailer.py) - ``email_id``
    e deterministico (``f"{user_id}:{ingestion_job_id}"``), o que da a
    idempotencia por ``email_id`` exigida pelo port ``Mailer`` sem
    precisar de logica extra: uma segunda chamada com o mesmo
    ``email_id`` acha a linha existente e nao duplica. Nao ha envio real
    (sem SES, ver i9-integration.md) - ``rendered_body`` e exatamente o
    que a pagina inicial exibe como previa.
    """

    __tablename__ = "email_digest"

    email_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    ingestion_job_id: Mapped[str] = mapped_column(String, nullable=False)
    notification_ids_json: Mapped[str] = mapped_column(String, nullable=False)
    rendered_body: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SearchExecution(Base):
    """Registro de uma execucao de POST /v1/search (Ticket 9, issue #25).

    Existe para satisfazer i7-reproducibility
    (requirements/perspec-me/capiwatt-lens-hackathon/concerns/i7-reproducibility.md):
    "Reexecutar significa rodar novamente a recuperacao e o ranking
    sobre o corpus preservado, usando o vetor da consulta registrada;
    consultar a resposta salva nao satisfaz esse requisito." Nesta fase
    demo (sem embeddings reais), "o corpus/vetor da consulta
    preservado" e ``raw_hits_json``: os hits CRUS devolvidos por
    ``AiClient.search`` (ver app/clients/ai_client.py::AiSearchHit),
    gravados ANTES do agrupamento por familia em app/routes/search.py -
    e o que ``app/replay.py::replay_search`` recomputa contra o
    catalogo atual, sem nunca chamar o ai de novo.

    ``response_json`` guarda o envelope final (``SearchEnvelope``) so
    para auditoria/comparacao manual - ``replay_search`` NAO devolve
    esse valor como sua resposta recomputada, so o usa para montar
    ``ReplayResult.original_response`` e comparar com o que foi
    recomputado (``ReplayResult.matches``).

    ``code_reference`` vem de ``Settings.code_reference`` (ver
    app/config.py) - a referencia de commit/ambiente no momento da
    busca, para auditoria.
    """

    __tablename__ = "search_execution"

    request_id: Mapped[str] = mapped_column(String, primary_key=True)
    query: Mapped[str] = mapped_column(String, nullable=False)
    data_mode: Mapped[str] = mapped_column(String, nullable=False)
    corpus_version: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    ranking_version: Mapped[str] = mapped_column(String, nullable=False)
    raw_hits_json: Mapped[str] = mapped_column(String, nullable=False)
    response_json: Mapped[str] = mapped_column(String, nullable=False)
    code_reference: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
