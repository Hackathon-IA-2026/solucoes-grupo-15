"""Modelos ORM do catalogo documental (TB1 Ticket 2, issue #18).

Escopo desta issue: so ``document_family`` e ``document_version``,
exatamente como o corpus de fixtures demo declara (ver
app/fixtures/demo_corpus.json). Nenhuma tabela de processo, relacao ou
sugestao de fusao e criada aqui - pertencem a tickets futuros (#21 e
outros; ver decisao d4-data-dictionary: processo SEI nao e familia,
fica fora de escopo).
"""

from sqlalchemy import ForeignKey, String
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
    issue #21).
    """

    __tablename__ = "document_version"

    document_version: Mapped[str] = mapped_column(String, primary_key=True)
    family_id: Mapped[str] = mapped_column(
        ForeignKey("document_family.family_id"), nullable=False
    )
    version_date: Mapped[str] = mapped_column(String, nullable=False)
    version_date_source: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    processo_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_text_locator: Mapped[str] = mapped_column(String, nullable=False)
    corpus_version: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)

    family: Mapped["DocumentFamily"] = relationship(back_populates="versions")
