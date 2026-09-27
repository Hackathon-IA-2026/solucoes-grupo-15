"""Rota de parecer conclusivo por processo.

GET /v1/processos/{processo_numero}/resultado devolve um OpinionOut com
os campos esperados pelo frontend (OpinionData em types/product.ts).

ATENÇÃO DE ROTA: este router deve ser incluído ANTES do relations_router
em main.py porque relations.py registra GET /v1/processos/{processo_id:path}
(catch-all). Se opinions_router for montado depois, o FastAPI despacha para
a rota catch-all do relations antes de chegar aqui.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1", tags=["opinions"])


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
    confidence: int
    coverage: int


@router.get("/processos/{processo_numero:path}/resultado", response_model=OpinionOut)
def get_resultado(processo_numero: str) -> OpinionOut:
    return OpinionOut(
        title=f"Parecer — {processo_numero}",
        processNumber=processo_numero,
        family="Corpus demonstrativo",
        theme="Fiscalização ANEEL",
        code="PC-stub-001",
        issuedAt="",
        status="Gerado pelo backend (stub)",
        verdict="Em análise",
        verdictSummary="Parecer gerado automaticamente pelo backend demonstrativo.",
        situation="Processo sob análise regulatória.",
        suggestedUnderstanding="Aguardando integração com LLM.",
        attentionPoints=["Stub — integração LLM pendente."],
        figures=[FigureOut(label="Confiança", value="n/d", tone="blue")],
        confidence=0,
        coverage=0,
    )
