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

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
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
