"""Rota publica de listagem de familias documentais (issue #116).

``GET /v1/families`` devolve um resumo por familia: o ``family_id``
(PK de ``document_family``), o tipo documental predominante
(``document_type`` da versao mais recente, via ``select_face_version``)
e a contagem de versoes cadastradas.

Retorna lista vazia se o catalogo ainda nao foi populado (ingestion
nunca rodou), nunca 404.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import select_face_version
from app.db import get_db_session
from app.models import DocumentFamily, DocumentVersion

router = APIRouter(prefix="/v1", tags=["families"])


class FamilySummary(BaseModel):
    family_id: str
    document_type: str
    versions_count: int


@router.get("/families", response_model=list[FamilySummary])
def list_families(db: Session = Depends(get_db_session)) -> list[FamilySummary]:
    """Lista todas as familias com contagem de versoes e tipo predominante."""
    # Contagem de versoes por familia
    counts_query = select(
        DocumentVersion.family_id,
        func.count(DocumentVersion.document_version).label("versions_count"),
    ).group_by(DocumentVersion.family_id)
    counts = {row.family_id: row.versions_count for row in db.execute(counts_query)}

    # Todas as familias
    families = db.scalars(select(DocumentFamily)).all()

    result: list[FamilySummary] = []
    for family in families:
        versions = family.versions
        face = select_face_version(versions)
        doc_type = face.document_type if face else "desconhecido"
        result.append(
            FamilySummary(
                family_id=family.family_id,
                document_type=doc_type,
                versions_count=counts.get(family.family_id, 0),
            )
        )
    return result
