"""Rota publica de ingestao do corpus fixture demo (TB1 Ticket 2, issue #18).

POST /v1/ingestions le o corpus de fixtures demo (app/fixtures/demo_corpus.json,
marcado "provisional": true - nunca dado real, ver
app/fixtures/loader.py), monta o payload para ``AiClient.index(...)`` e
faz upsert do catalogo (``document_family``, ``document_version``) no
Postgres a partir dos ``IndexReport``s devolvidos.

Idempotencia: reingerir a mesma fixture faz upsert por PK (nao duplica
linhas) e a chamada a ``ai.index`` para os mesmos ``document_version``
bate no caminho idempotente do ai (mesmo relatorio, arquivo nao
reescrito).

``ingestion_job_id`` e gerado aqui como um id simples (uuid4), mesmo
sem tabela de "job" ainda - tickets futuros de notificacao (#24) devem
reusar este identificador.
"""

import uuid
from dataclasses import dataclass

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clients.ai_client import AiClient, IndexDocumentPayload, IndexReport, get_ai_client
from app.db import get_db_session
from app.fixtures.loader import FixtureCorpus, FixtureDocumentVersion, load_demo_corpus
from app.models import DocumentFamily, DocumentVersion

router = APIRouter(prefix="/v1", tags=["ingestions"])


@dataclass(frozen=True)
class IngestionResult:
    ingestion_job_id: str
    families_count: int
    versions_count: int


@router.post("/ingestions")
def create_ingestion(
    ai_client: AiClient = Depends(get_ai_client),
    session: Session = Depends(get_db_session),
) -> dict[str, str | int]:
    corpus = load_demo_corpus()
    result = run_ingestion(corpus, ai_client=ai_client, session=session)
    return {
        "ingestion_job_id": result.ingestion_job_id,
        "families_count": result.families_count,
        "versions_count": result.versions_count,
    }


def run_ingestion(
    corpus: FixtureCorpus, *, ai_client: AiClient, session: Session
) -> IngestionResult:
    reports_by_version = _index_corpus(corpus, ai_client)

    family_ids: set[str] = set()
    version_ids: set[str] = set()

    for doc in corpus.documents:
        report = reports_by_version[doc.document_version]
        _upsert_family(session, doc.family_id)
        _upsert_version(session, doc, report, corpus.corpus_version)
        family_ids.add(doc.family_id)
        version_ids.add(doc.document_version)

    session.flush()

    return IngestionResult(
        ingestion_job_id=str(uuid.uuid4()),
        families_count=len(family_ids),
        versions_count=len(version_ids),
    )


def _index_corpus(corpus: FixtureCorpus, ai_client: AiClient) -> dict[str, IndexReport]:
    payload = [
        IndexDocumentPayload(document_version=doc.document_version, text=doc.text)
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
