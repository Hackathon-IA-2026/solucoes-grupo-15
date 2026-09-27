"""Rota publica de listagem de temas regulatorios (issue #118).

``GET /v1/themes`` consulta o modulo de IA (F2) via ``AiClient.get_themes()``
e retorna a taxonomia de temas com descricao oficial, tipos de processo
e status.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.clients.ai_client import AiClient, get_ai_client

router = APIRouter(prefix="/v1", tags=["themes"])


class ThemeOut(BaseModel):
    id: str
    name: str
    description: str
    tipos_processo: list[str] = []
    status: str = "Disponível"


@router.get("/themes", response_model=list[ThemeOut])
def list_themes(ai_client: AiClient = Depends(get_ai_client)) -> list[ThemeOut]:
    """Lista todos os temas regulatorios com suas descricoes."""
    themes = ai_client.get_themes()
    return [
        ThemeOut(
            id=t.tema_id,
            name=t.tema_nome,
            description=t.descricao,
            tipos_processo=t.tipos_processo,
            status="Disponível",
        )
        for t in themes
    ]
