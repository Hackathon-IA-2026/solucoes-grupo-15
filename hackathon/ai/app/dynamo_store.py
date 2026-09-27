import boto3
from boto3.dynamodb.conditions import Key
from typing import Optional, List, Dict
from botocore.exceptions import ClientError
from datetime import datetime
import json
import os

from .models import ProcessClassification, TemaTaxonomy
from .theme_store import ProcessThemeClassifier
from .theme_descriptions import get_theme_description
from .config import settings

class InMemoryProcessThemeStore(ProcessThemeClassifier):
    def __init__(self, data: List[dict] = None):
        self.store: Dict[str, ProcessClassification] = {}
        if data is not None:
            for item in data:
                if not item.get("descricao"):
                    item["descricao"] = get_theme_description(item.get("tema_id", ""), item.get("tema_nome", ""))
                obj = ProcessClassification(**item)
                self.store[obj.tipo_processo] = obj
        else:
            fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "process_themes.json")
            if os.path.exists(fixture_path):
                self.load_from_file(fixture_path)

    def load_from_file(self, filepath: str):
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    if not item.get("descricao"):
                        item["descricao"] = get_theme_description(item.get("tema_id", ""), item.get("tema_nome", ""))
                    obj = ProcessClassification(**item)
                    self.store[obj.tipo_processo] = obj

    def get_theme(self, tipo_processo: str) -> Optional[ProcessClassification]:
        return self.store.get(tipo_processo)

    def list_themes(self) -> List[TemaTaxonomy]:
        themes: Dict[str, TemaTaxonomy] = {}
        for obj in self.store.values():
            tema_id = obj.tema_id
            if tema_id not in themes:
                themes[tema_id] = TemaTaxonomy(
                    tema_id=tema_id,
                    tema_nome=obj.tema_nome,
                    descricao=getattr(obj, "descricao", "") or get_theme_description(tema_id, obj.tema_nome),
                    tipos_processo=[]
                )
            themes[tema_id].tipos_processo.append(obj.tipo_processo)
        
        for theme in themes.values():
            theme.tipos_processo.sort()
            
        return sorted(list(themes.values()), key=lambda x: x.tema_nome)

    def get_types_by_theme(self, tema_id: str) -> List[str]:
        types = [
            obj.tipo_processo 
            for obj in self.store.values() 
            if obj.tema_id == tema_id
        ]
        return sorted(types)


class DynamoProcessThemeStore(ProcessThemeClassifier):
    def __init__(self, fallback: Optional[ProcessThemeClassifier] = None):
        client_kwargs = {
            "region_name": settings.aws_region
        }
        if settings.dynamodb_endpoint_url:
            client_kwargs["endpoint_url"] = settings.dynamodb_endpoint_url

        self.dynamodb = boto3.resource("dynamodb", **client_kwargs)
        self.table = self.dynamodb.Table(settings.dynamodb_table_process_themes)
        self.fallback = fallback if fallback is not None else InMemoryProcessThemeStore()

    def get_theme(self, tipo_processo: str) -> Optional[ProcessClassification]:
        try:
            response = self.table.get_item(
                Key={"tipo_processo": tipo_processo},
                ConsistentRead=False
            )
            item = response.get("Item")
            if item:
                return ProcessClassification(**item)
        except Exception:
            pass
        return self.fallback.get_theme(tipo_processo)

    def list_themes(self) -> List[TemaTaxonomy]:
        try:
            response = self.table.scan(ConsistentRead=False)
            items = response.get("Items", [])
            if not items:
                return self.fallback.list_themes()
            
            # Aggregate by tema_id
            themes: Dict[str, TemaTaxonomy] = {}
            for item in items:
                tema_id = item.get("tema_id")
                if not tema_id:
                    continue
                
                if tema_id not in themes:
                    themes[tema_id] = TemaTaxonomy(
                        tema_id=tema_id,
                        tema_nome=item.get("tema_nome", ""),
                        descricao=item.get("descricao") or get_theme_description(tema_id, item.get("tema_nome", "")),
                        tipos_processo=[]
                    )
                themes[tema_id].tipos_processo.append(item.get("tipo_processo"))
            
            # Sort the types in each theme
            for theme in themes.values():
                theme.tipos_processo.sort()

            # Sort themes by name
            return sorted(list(themes.values()), key=lambda x: x.tema_nome)
        except Exception:
            return self.fallback.list_themes()

    def get_types_by_theme(self, tema_id: str) -> List[str]:
        try:
            response = self.table.query(
                IndexName="GSI_Tema",
                KeyConditionExpression=Key("tema_id").eq(tema_id)
            )
            items = response.get("Items", [])
            if items:
                return sorted([item.get("tipo_processo") for item in items])
        except Exception:
            pass
        return self.fallback.get_types_by_theme(tema_id)
