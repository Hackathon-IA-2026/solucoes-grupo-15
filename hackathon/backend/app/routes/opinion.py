"""Ficha demonstrativa de parecer baseada em documentos do caso 1.

Nao ha geracao automatica de conclusao: os trechos sao copiados da
fixture documental e o PDF original continua sendo a referencia.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import select_face_version
from app.db import get_db_session
from app.fixtures.loader import load_demo_corpus
from app.models import DocumentVersion

router = APIRouter(prefix="/v1", tags=["opinion"])


class FigureOut(BaseModel):
    label: str
    value: str
    tone: str


class OpinionOut(BaseModel):
    title: str
    processNumber: str
    family: str
    theme: str
    code: str
    issuedAt: str
    status: str
    verdict: str
    verdictSummary: str
    situation: str
    suggestedUnderstanding: str
    attentionPoints: list[str]
    figures: list[FigureOut]
    confidence: int | None
    coverage: int | None


@router.get("/opinion", response_model=OpinionOut)
def get_demo_opinion(session: Session = Depends(get_db_session)) -> OpinionOut:
    family_ids = ("case1-coelba-voto", "case1-enel-voto", "case1-cemig-voto")
    corpus = load_demo_corpus()
    excerpts = {doc.family_id: doc.text for doc in corpus.documents if doc.family_id in family_ids}
    versions_by_family: dict[str, list[DocumentVersion]] = {}
    for version in session.scalars(
        select(DocumentVersion).where(DocumentVersion.family_id.in_(family_ids))
    ).all():
        versions_by_family.setdefault(version.family_id, []).append(version)
    if len(excerpts) != len(family_ids) or len(versions_by_family) != len(family_ids):
        raise HTTPException(status_code=404, detail="Corpus demonstrativo nao ingerido")

    coelba = select_face_version(versions_by_family["case1-coelba-voto"])
    return OpinionOut(
        title="Parecer conclusivo demonstrativo — conexão de MMGD",
        processNumber=coelba.processo_numero or "",
        family="Caso 1 · Carolina",
        theme="Fiscalização do atendimento às solicitações de conexão de MMGD",
        code="DEMO-CASE1-MMGD",
        issuedAt=coelba.version_date,
        status="Demonstração documental",
        verdict="Trechos de precedentes para revisão",
        verdictSummary=excerpts["case1-coelba-voto"],
        situation=excerpts["case1-cemig-voto"],
        suggestedUnderstanding=excerpts["case1-enel-voto"],
        attentionPoints=[
            "Os trechos exibidos são extratos de documentos, sem análise jurídica automatizada.",
            "Consulte os PDFs originais antes de usar qualquer conclusão profissional.",
        ],
        figures=[
            FigureOut(label="Votos citados", value="3", tone="green"),
            FigureOut(label="Documentos no caso 1", value=str(sum(
                doc.family_id.startswith("case1-") for doc in corpus.documents
            )), tone="blue"),
        ],
        confidence=None,
        coverage=None,
    )
