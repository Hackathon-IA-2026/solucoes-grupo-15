from fastapi import APIRouter, Depends, HTTPException, Path as RoutePath
from typing import List

from ..models import ProcessClassification, TemaTaxonomy
from ..theme_store import ProcessThemeClassifier
from ..dynamo_store import DynamoProcessThemeStore

router = APIRouter(prefix="/internal/v1", tags=["internal"])

# Provide the singleton or instantiate it
_store_instance = None

def get_theme_store() -> ProcessThemeClassifier:
    global _store_instance
    if _store_instance is None:
        _store_instance = DynamoProcessThemeStore()
    return _store_instance

@router.get("/process-classification/{tipo_processo:path}", response_model=ProcessClassification)
def resolve_process_classification(
    tipo_processo: str = RoutePath(..., description="Tipo de processo (ex: 'Outorga de Distribuição: Compartilhamento de Infraestrutura')"),
    store: ProcessThemeClassifier = Depends(get_theme_store)
) -> ProcessClassification:
    classification = store.get_theme(tipo_processo)
    if classification is None:
        # User story 4: graceful fallback classification if not found
        # Or should we return 404? "tratamento de tipos não cadastrados (404 ou fallback gracioso)"
        # Let's return 404 since F3 or ai can handle it. The issue says: 
        # "4. As an indexing worker, I want to query DynamoDB for unclassified process types and receive a safe fallback classification (e.g., "Pendente de Classificação"), so that ingestion never crashes on novel SEI types."
        # If we return a fallback classification here:
        return ProcessClassification(
            tipo_processo=tipo_processo,
            tema_id="pendente-classificacao",
            tema_nome="Pendente de Classificação",
            macrotema_sei="Desconhecido",
            temas_secundarios=[],
            origem_classificacao="inferida",
            atualizado_em=""
        )
    return classification

@router.get("/process-types/themes", response_model=List[TemaTaxonomy])
def list_process_themes(
    store: ProcessThemeClassifier = Depends(get_theme_store)
) -> List[TemaTaxonomy]:
    return store.list_themes()
