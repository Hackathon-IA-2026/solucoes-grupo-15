"""Rota interna de busca (adapter demo) do modulo ai.

Cobre, para o Ticket 3 (TB1, issue #19), a operacao ``search`` do port
VectorService (issue #16). Nao ha busca vetorial real, embeddings ou
calculo de similaridade: a resposta vem inteiramente de um mapeamento
declarativo fixo, definido em app/fixtures/search_fixtures.json
(marcado ``"provisional": true``) - consulta (string exata) -> lista
ordenada de hits. O ai le esse arquivo diretamente e resolve a busca
sozinho: recebe so a ``query`` por HTTP, nunca os dados de busca em si
(o backend nao repassa um payload de dados aqui, ao contrario de
``index``).

Correspondencia e SEMPRE exata (sem fuzzy matching, sem NLP, sem
normalizacao de acentos/caixa). Uma consulta que nao esta declarada na
fixture NAO e erro: devolve 200 com ``hits: []``.

O agrupamento por familia (uma familia nunca duas vezes na resposta,
face = versao mais recente) e responsabilidade do backend (POST
/v1/search, ver hackathon/backend/app/routes/search.py) - esta rota
devolve os hits crus, na ordem exatamente declarada na fixture, sem
agrupar nem reordenar por score.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.routes.index import MODEL_VERSION

router = APIRouter(prefix="/internal/v1", tags=["internal"])

_DEFAULT_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "search_fixtures.json"


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class SearchHitOut(BaseModel):
    family_id: str
    document_version: str
    excerpt: str
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHitOut]
    model_version: str


def get_search_fixture_path() -> Path:
    """Dependencia FastAPI para o caminho do fixture de busca.

    Testes podem sobrescrever (dependency_overrides) para apontar a um
    arquivo temporario, seguindo o mesmo padrao de get_documents_root
    (app/routes/index.py).
    """
    return _DEFAULT_FIXTURE_PATH


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    fixture_path: Path = Depends(get_search_fixture_path),
) -> SearchResponse:
    queries = _load_queries(fixture_path)
    hits = queries.get(payload.query, [])
    if payload.top_k is not None:
        hits = hits[: payload.top_k]
    return SearchResponse(
        hits=[SearchHitOut(**hit) for hit in hits],
        model_version=MODEL_VERSION,
    )


def _load_queries(fixture_path: Path) -> dict[str, list[dict]]:
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    return raw["queries"]
