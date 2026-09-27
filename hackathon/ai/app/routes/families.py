"""Rota interna ``similar_families`` do port VectorService (issue #92).

``GET /internal/v1/families/{family_id}/similar?top_k=3`` devolve os
candidatos de vizinhanca vetorial da familia (ver
app/family_similarity.py): ``{family_id, model_version, similar:
[{family_id, score}]}``. ``top_k`` padrao = 3, o k fixado na issue-13 e
usado na calibracao das issues #61/#74.

- Modo real (``EMBEDDER=bedrock``/``cached``): le os embeddings do indice
  do ``model_version`` atual; familia sem chunk no indice -> 404.
- Modo fixture (``EMBEDDER=fake``): nao ha vetores, entao nao ha
  candidatos - 200 com ``similar: []`` para qualquer familia.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import REAL_PIPELINE_EMBEDDERS, get_settings
from app.embeddings import MODEL_VERSION as REAL_MODEL_VERSION
from app.family_similarity import UnknownFamily, similar_families
from app.routes.index import MODEL_VERSION, get_vector_store
from app.vector_store import VectorStore, index_name_for_model_version

router = APIRouter(prefix="/internal/v1", tags=["internal"])

DEFAULT_TOP_K = 3


class SimilarFamilyOut(BaseModel):
    family_id: str
    score: float


class SimilarFamiliesResponse(BaseModel):
    family_id: str
    model_version: str
    similar: list[SimilarFamilyOut]


@router.get("/families/{family_id}/similar", response_model=SimilarFamiliesResponse)
def get_similar_families(
    family_id: str,
    top_k: int = Query(DEFAULT_TOP_K, ge=1),
    vector_store: VectorStore = Depends(get_vector_store),
) -> SimilarFamiliesResponse:
    if get_settings().embedder not in REAL_PIPELINE_EMBEDDERS:
        return SimilarFamiliesResponse(family_id=family_id, model_version=MODEL_VERSION, similar=[])

    embeddings = vector_store.embeddings_by_family(index_name_for_model_version(REAL_MODEL_VERSION))
    try:
        neighbors = similar_families(family_id, embeddings, top_k)
    except UnknownFamily as exc:
        raise HTTPException(
            status_code=404, detail=f"Familia sem chunks no indice: {family_id!r}"
        ) from exc
    return SimilarFamiliesResponse(
        family_id=family_id,
        model_version=REAL_MODEL_VERSION,
        similar=[SimilarFamilyOut(family_id=n.family_id, score=n.score) for n in neighbors],
    )
