"""Rota publica de ingestao do corpus fixture demo (TB1 Ticket 2, issue #18;
relacoes adicionadas no Ticket 5, issue #21).

POST /v1/ingestions le o corpus de fixtures demo (app/fixtures/demo_corpus.json,
marcado "provisional": true - nunca dado real, ver
app/fixtures/loader.py), monta o payload para ``AiClient.index(...)`` e
faz upsert do catalogo (``document_family``, ``document_version``) no
Postgres a partir dos ``IndexReport``s devolvidos. Na mesma chamada,
tambem le a fixture de relacoes (app/fixtures/demo_relations.json,
Ticket 5) e faz upsert de ``document_relations`` - nenhuma extracao de
padrao textual roda aqui, as arestas vem literalmente da fixture (ver
app/fixtures/relations_loader.py).

Idempotencia: reingerir a mesma fixture faz upsert por PK (nao duplica
linhas de catalogo) e por chave natural
``(source_id, source_kind, target_id, target_kind, type)`` (nao
duplica linhas de relacao) - a chamada a ``ai.index`` para os mesmos
``document_version`` bate no caminho idempotente do ai (mesmo
relatorio, arquivo nao reescrito).

``ingestion_job_id`` e gerado aqui como um id simples (uuid4), mesmo
sem tabela de "job" ainda - reusado por ``run_notifications``
(app/notifications.py, Ticket 8, issue #24), chamada ao fim desta
funcao para gerar notificacoes + digest de e-mail para os usuarios que
ja escolheram ``notification_scope``. Ao contrario de ``relations``,
essa chamada nao e opcional: roda sempre, depois do upsert de catalogo
e relacoes - com zero usuarios de escopo escolhido (cenario dos testes
dos Tickets 2-5/7/9) e um no-op seguro.
"""

import uuid
from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.ai_client import AiClient, IndexDocumentPayload, IndexReport, get_ai_client
from app.db import get_db_session
from app.fixtures.case1_loader import CASE1_REAL_CORPUS_VERSION, load_case1_real_corpus
from app.fixtures.loader import FixtureCorpus, FixtureDocumentVersion, load_demo_corpus
from app.fixtures.relations_loader import (
    FixtureRelation,
    FixtureRelations,
    load_demo_relations,
)
from app.models import DocumentFamily, DocumentRelation, DocumentVersion
from app.notifications import run_notifications

router = APIRouter(prefix="/v1", tags=["ingestions"])


@dataclass(frozen=True)
class IngestionResult:
    ingestion_job_id: str
    families_count: int
    versions_count: int
    relations_count: int
    # Soma de IndexReport.total_input_tokens (issue #73, AC "custo de
    # embeddings") - None no modo fixture (EMBEDDER=fake nao computa
    # embeddings reais, ver ai/app/routes/index.py::IndexReport).
    total_input_tokens: int | None = None


class IngestionRequestIn(BaseModel):
    """Corpo opcional de POST /v1/ingestions (issue #88).

    Sem corpo (ou ``corpus="demo"``), mantem o comportamento original:
    fixture demo + relacoes da fixture. ``corpus="case1-real"`` ingere os
    10 documentos reais do caso 1 (Markdown completo da issue #59, ver
    app/fixtures/case1_loader.py) sem relacoes de fixture - arestas de um
    corpus real devem vir do ai (``similar_families``/``references``),
    nunca de dado demo. ``corpus_version`` (so para ``case1-real``)
    registra o hash do manifesto da issue #68 no catalogo.
    """

    corpus: Literal["demo", "case1-real"] = "demo"
    corpus_version: str | None = None


@router.post("/ingestions")
def create_ingestion(
    payload: IngestionRequestIn | None = None,
    ai_client: AiClient = Depends(get_ai_client),
    session: Session = Depends(get_db_session),
) -> dict[str, str | int]:
    payload = payload or IngestionRequestIn()
    if payload.corpus == "case1-real":
        corpus = load_case1_real_corpus(
            corpus_version=payload.corpus_version or CASE1_REAL_CORPUS_VERSION
        )
        relations = None
    else:
        corpus = load_demo_corpus()
        relations = load_demo_relations()
    result = run_ingestion(
        corpus, ai_client=ai_client, session=session, relations=relations
    )
    return {
        "ingestion_job_id": result.ingestion_job_id,
        "families_count": result.families_count,
        "versions_count": result.versions_count,
        "relations_count": result.relations_count,
    }


def run_ingestion(
    corpus: FixtureCorpus,
    *,
    ai_client: AiClient,
    session: Session,
    relations: FixtureRelations | None = None,
) -> IngestionResult:
    """Ingere o corpus documental e, opcionalmente, as relacoes.

    ``relations`` e opcional (``None`` por padrao) so para nao quebrar
    os chamadores dos Tickets 2-4 (testes existentes que ingerem so o
    corpus, sem relacoes) - POST /v1/ingestions sempre passa a fixture
    de relacoes carregada (ver ``create_ingestion`` acima).
    """
    ingestion_job_id = str(uuid.uuid4())

    reports_by_version = _index_corpus(corpus, ai_client)

    family_ids: set[str] = set()
    version_ids: set[str] = set()

    for doc in corpus.documents:
        report = reports_by_version[doc.document_version]
        _upsert_family(session, doc.family_id)
        _upsert_version(session, doc, report, corpus.corpus_version)
        family_ids.add(doc.family_id)
        version_ids.add(doc.document_version)

    relations_count = 0
    if relations is not None:
        relations_count = run_relations_ingestion(relations, session=session)

    run_notifications(corpus, session=session, ingestion_job_id=ingestion_job_id)

    session.flush()

    token_counts = [r.total_input_tokens for r in reports_by_version.values()]
    total_input_tokens = sum(token_counts) if all(t is not None for t in token_counts) else None

    return IngestionResult(
        ingestion_job_id=ingestion_job_id,
        families_count=len(family_ids),
        versions_count=len(version_ids),
        relations_count=relations_count,
        total_input_tokens=total_input_tokens,
    )


def run_relations_ingestion(relations: FixtureRelations, *, session: Session) -> int:
    """Faz upsert das arestas declaradas pela fixture de relacoes.

    Upsert pela chave natural ``(source_id, source_kind, target_id,
    target_kind, type)`` - unica em ``document_relations`` (ver
    ``models.py``). Reingerir a mesma fixture nao duplica linhas.
    """
    for rel in relations.relations:
        _upsert_relation(session, rel)
    session.flush()
    return len(relations.relations)


def _upsert_relation(session: Session, rel: FixtureRelation) -> None:
    existing = session.scalar(
        select(DocumentRelation).where(
            DocumentRelation.source_id == rel.source_id,
            DocumentRelation.source_kind == rel.source_kind,
            DocumentRelation.target_id == rel.target_id,
            DocumentRelation.target_kind == rel.target_kind,
            DocumentRelation.type == rel.type,
        )
    )
    if existing is None:
        existing = DocumentRelation(
            source_id=rel.source_id,
            source_kind=rel.source_kind,
            target_id=rel.target_id,
            target_kind=rel.target_kind,
            type=rel.type,
        )
        session.add(existing)

    existing.origin = rel.origin
    existing.status = rel.status
    existing.evidence_document_version = (
        rel.evidence.document_version if rel.evidence is not None else None
    )
    existing.evidence_locator = rel.evidence.locator if rel.evidence is not None else None


def _index_corpus(corpus: FixtureCorpus, ai_client: AiClient) -> dict[str, IndexReport]:
    """Monta o payload de ``ai_client.index`` a partir do corpus.

    ``family_id``/``corpus_version`` (issue #69) sao enviados junto do
    texto para que o ai real (EMBEDDER=bedrock) tenha os atributos de
    filtro que precisa gravar por chunk - o adapter de fixture
    (EMBEDDER=fake) continua ignorando os dois, como antes.
    """
    payload = [
        IndexDocumentPayload(
            document_version=doc.document_version,
            text=doc.text,
            family_id=doc.family_id,
            corpus_version=corpus.corpus_version,
        )
        for doc in corpus.documents
    ]
    reports = ai_client.index(payload)
    return {report.document_version: report for report in reports}


def _upsert_family(session: Session, family_id: str) -> None:
    if session.get(DocumentFamily, family_id) is None:
        session.add(DocumentFamily(family_id=family_id))


def _upsert_version(
    session: Session,
    doc: FixtureDocumentVersion,
    report: IndexReport,
    corpus_version: str,
) -> None:
    version = session.get(DocumentVersion, doc.document_version)
    if version is None:
        version = DocumentVersion(document_version=doc.document_version)
        session.add(version)

    version.family_id = doc.family_id
    version.document_id = doc.document_id
    version.version_date = doc.version_date
    version.version_date_source = doc.version_date_source
    version.document_type = doc.document_type
    version.processo_numero = doc.processo_numero
    version.extracted_text_locator = report.extracted_text_locator
    version.corpus_version = corpus_version
    version.model_version = report.model_version
