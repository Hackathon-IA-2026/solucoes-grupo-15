"""Rota publica de leitura de documento por familia+versao (TB1 Ticket 4, issue #20).

``GET /v1/documents/{family_id}`` devolve o cabecalho de uma familia
(tipo, ``document_id`` cru da fixture como identificador de exibicao -
sem nenhuma regra de formatacao por tipo documental, isso pertence as
issues #10-#14 - e o processo SEI ao qual pertence, se houver), a
linha do tempo completa de versoes (mais recente primeiro) e o texto
extraido da versao selecionada.

Selecao de versao: o query param opcional ``version`` (um
``document_version``) escolhe a versao exibida; se omitido, ou se o
valor passado nao pertencer a familia, cai para a "face" (versao de
maior ``version_date`` - mesma regra de ``select_face_version``,
app/catalog.py, ja usada por POST /v1/search desde o Ticket 3).

Leitura de texto: ``extracted_text_locator`` e um caminho de
filesystem no volume compartilhado com o ai (``documents-data``,
montado tambem no backend - ver hackathon/docker-compose.yml), lido
diretamente daqui. Se o arquivo nao existir por algum motivo, devolve
404 em vez de deixar a excecao virar 500.

Familia inexistente no catalogo -> 404.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import select_face_version
from app.db import get_db_session
from app.models import DocumentVersion

router = APIRouter(prefix="/v1", tags=["documents"])


class VersionSummary(BaseModel):
    document_version: str
    version_date: str
    version_date_source: str


class SelectedVersionOut(BaseModel):
    document_version: str
    version_date: str
    version_date_source: str
    text: str


class DocumentDetailOut(BaseModel):
    family_id: str
    document_id: str
    document_type: str
    processo_numero: str | None
    versions: list[VersionSummary]
    selected_version: SelectedVersionOut


@router.get("/documents/{family_id}", response_model=DocumentDetailOut)
def get_document(
    family_id: str,
    version: str | None = None,
    session: Session = Depends(get_db_session),
) -> DocumentDetailOut:
    versions = session.scalars(
        select(DocumentVersion).where(DocumentVersion.family_id == family_id)
    ).all()
    if not versions:
        raise HTTPException(status_code=404, detail="Familia nao encontrada")

    selected = _select_version(versions, version)
    text = _read_extracted_text(selected)
    ordered = sorted(versions, key=lambda v: v.version_date, reverse=True)

    return DocumentDetailOut(
        family_id=family_id,
        document_id=selected.document_id,
        document_type=selected.document_type,
        processo_numero=selected.processo_numero,
        versions=[
            VersionSummary(
                document_version=v.document_version,
                version_date=v.version_date,
                version_date_source=v.version_date_source,
            )
            for v in ordered
        ],
        selected_version=SelectedVersionOut(
            document_version=selected.document_version,
            version_date=selected.version_date,
            version_date_source=selected.version_date_source,
            text=text,
        ),
    )


def _select_version(
    versions: list[DocumentVersion], requested: str | None
) -> DocumentVersion:
    if requested is not None:
        for candidate in versions:
            if candidate.document_version == requested:
                return candidate
    return select_face_version(versions)


def _read_extracted_text(version: DocumentVersion) -> str:
    path = Path(version.extracted_text_locator)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(
            status_code=404,
            detail="Texto extraido nao encontrado para esta versao",
        ) from exc
