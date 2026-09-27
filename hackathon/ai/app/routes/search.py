"""Rota interna de busca do modulo ai.

Cobre a operacao ``search`` do port VectorService (issue #16), em dois
modos escolhidos por ``Settings.embedder`` (variavel ``EMBEDDER``, ver
app/config.py) - o mesmo toggle usado por app/routes/index.py:

- ``EMBEDDER=fake`` (default, Ticket 3/TB1): adapter demo original. Nao
  ha busca vetorial real: a resposta vem de um mapeamento declarativo
  fixo (app/fixtures/search_fixtures.json, ``"provisional": true``) -
  consulta (string exata) -> lista ordenada de hits. Correspondencia e
  SEMPRE exata (sem fuzzy matching/NLP/normalizacao). Uma consulta nao
  declarada devolve 200 com ``hits: []``. Preservado byte-a-byte (issue
  #69, AC "modo fixture continua funcionando sem credenciais AWS").

- ``EMBEDDER=bedrock`` (issue #69): embeda a ``query`` com o mesmo
  adapter Titan V2 usado por ``index`` (app/embeddings.py) e busca no
  indice vetorial real (app/vector_store.py) os ``top_k`` chunks mais
  proximos por produto escalar (vetores normalizados == cosseno, mesma
  escolha do protototipo do Recall@3, issue #60). Devolve hits crus por
  chunk, na ordem de score (maior primeiro) - o agrupamento por familia
  continua responsabilidade exclusiva do backend (POST /v1/search, ver
  hackathon/backend/app/routes/search.py). ``model_version`` de
  resposta e ``app.embeddings.MODEL_VERSION``.

O agrupamento por familia (uma familia nunca duas vezes na resposta,
face = versao mais recente) e responsabilidade do backend nos dois
modos - esta rota nunca agrupa nem reordena por conta propria alem do
proprio ranking por score (no modo real) ou da ordem declarada (no modo
fake).
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.chunking import chunk_index_from_id
from app.config import REAL_PIPELINE_EMBEDDERS, get_settings
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.embeddings import BedrockEmbedder
from app.routes.index import MODEL_VERSION, get_embedder, get_vector_store
from app.vector_store import VectorStore, index_name_for_model_version

router = APIRouter(prefix="/internal/v1", tags=["internal"])

_DEFAULT_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "search_fixtures.json"

# Default de top_k quando o modo real e usado sem o parametro explicito -
# a issue #60 mediu Recall@3 com top_k=3; um default mais generoso (10)
# evita truncar demais uma busca de uso geral (issue #73, corpus maior)
# quando o chamador nao pede um top_k especifico.
DEFAULT_REAL_TOP_K = 10


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class SearchHitOut(BaseModel):
    """Um hit cru por chunk.

    ``chunk_id`` (issue #96) e o id estavel do chunk no indice
    (``"<document_version>#chunk-NNNN"``, ver app/chunking.py) e
    ``chunk_index`` e o indice real do chunk dentro do documento
    (0-based) - nunca a posicao do hit nesta lista. Juntos com
    ``document_version`` identificam o chunk para feedback (#82) e
    ``evidence_refs`` (#66).
    """

    family_id: str
    document_version: str
    chunk_id: str
    chunk_index: int
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
    embedder: BedrockEmbedder = Depends(get_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
) -> SearchResponse:
    if get_settings().embedder in REAL_PIPELINE_EMBEDDERS:
        return _search_real(payload, embedder, vector_store)
    return _search_fake(payload, fixture_path)


def _search_fake(payload: SearchRequest, fixture_path: Path) -> SearchResponse:
    queries = _load_queries(fixture_path)
    hits = queries.get(payload.query, [])
    if payload.top_k is not None:
        hits = hits[: payload.top_k]
    return SearchResponse(
        hits=[
            SearchHitOut(**hit, chunk_index=chunk_index_from_id(hit["chunk_id"]))
            for hit in hits
        ],
        model_version=MODEL_VERSION,
    )


def _search_real(
    payload: SearchRequest, embedder: BedrockEmbedder, vector_store: VectorStore
) -> SearchResponse:
    top_k = payload.top_k if payload.top_k is not None else DEFAULT_REAL_TOP_K
    query_vector = embedder.embed_text(payload.query).vector
    index_name = index_name_for_model_version(REAL_MODEL_VERSION)
    hits = vector_store.search(index_name, query_vector, top_k)
    return SearchResponse(
        hits=[
            SearchHitOut(
                family_id=hit.family_id,
                document_version=hit.document_version,
                chunk_id=hit.chunk_id,
                chunk_index=chunk_index_from_id(hit.chunk_id),
                excerpt=hit.excerpt,
                score=hit.score,
            )
            for hit in hits
        ],
        model_version=REAL_MODEL_VERSION,
    )


def _load_queries(fixture_path: Path) -> dict[str, list[dict]]:
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    queries = dict(raw["queries"])
    for alias, target in raw.get("aliases", {}).items():
        queries[alias] = queries.get(target, [])
    return queries
