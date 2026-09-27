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

class DynamoProcessThemeStore(ProcessThemeClassifier):
    def __init__(self):
        # We allow injecting endpoint_url for localstack/moto
        client_kwargs = {
            "region_name": settings.aws_region
        }
        if settings.dynamodb_endpoint_url:
            client_kwargs["endpoint_url"] = settings.dynamodb_endpoint_url

        self.dynamodb = boto3.resource("dynamodb", **client_kwargs)
        self.table = self.dynamodb.Table(settings.dynamodb_table_process_themes)

    def get_theme(self, tipo_processo: str) -> Optional[ProcessClassification]:
        try:
            response = self.table.get_item(
                Key={"tipo_processo": tipo_processo},
                ConsistentRead=False
            )
            item = response.get("Item")
            if not item:
                return None
            return ProcessClassification(**item)
        except ClientError as e:
            # Depending on error, we might log it. For now return None.
            return None

    def list_themes(self) -> List[TemaTaxonomy]:
        # To list all themes and their process types, a full scan is needed 
        # unless we maintain a separate index or aggregate. 
        # Given the small size of the table (51 items), a scan is very fast.
        try:
            response = self.table.scan(ConsistentRead=False)
            items = response.get("Items", [])
            
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
        except ClientError:
            return []

    def get_types_by_theme(self, tema_id: str) -> List[str]:
        try:
            response = self.table.query(
                IndexName="GSI_Tema",
                KeyConditionExpression=Key("tema_id").eq(tema_id)
            )
            items = response.get("Items", [])
            return sorted([item.get("tipo_processo") for item in items])
        except ClientError:
            return []


class InMemoryProcessThemeStore(ProcessThemeClassifier):
    def __init__(self, data: List[dict] = None):
        self.store: Dict[str, ProcessClassification] = {}
        if data is not None:
            for item in data:
                if not item.get("descricao"):
                    item["descricao"] = get_theme_description(item.get("tema_id", ""), item.get("tema_nome", ""))
                obj = ProcessClassification(**item)
                self.store[obj.tipo_processo] = obj

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
