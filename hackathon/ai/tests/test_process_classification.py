import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
import boto3

from app.main import app
from app.config import settings
from app.routes.process_classification import get_theme_store
from app.dynamo_store import DynamoProcessThemeStore, InMemoryProcessThemeStore
from app.models import ProcessClassification

@pytest.fixture
def mock_dynamodb():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        table = dynamodb.create_table(
            TableName=settings.dynamodb_table_process_themes,
            KeySchema=[{"AttributeName": "tipo_processo", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "tipo_processo", "AttributeType": "S"},
                {"AttributeName": "tema_id", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI_Tema",
                    "KeySchema": [{"AttributeName": "tema_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        yield table

@pytest.fixture
def store(mock_dynamodb):
    # This will use the mock AWS environment provided by moto
    return DynamoProcessThemeStore()

@pytest.fixture
def in_memory_store():
    data = [
        {
            "tipo_processo": "Outorga de Distribuição: Compartilhamento de Infraestrutura",
            "tema_id": "compartilhamento-de-infraestrutura",
            "tema_nome": "Compartilhamento de infraestrutura",
            "macrotema_sei": "Outorga de Distribuição",
            "temas_secundarios": [],
            "origem_classificacao": "direta",
            "atualizado_em": "2026-09-26T00:00:00Z"
        }
    ]
    return InMemoryProcessThemeStore(data)

def test_dynamo_store_get_theme(store, mock_dynamodb):
    mock_dynamodb.put_item(Item={
        "tipo_processo": "Outorga de Distribuição: Compartilhamento de Infraestrutura",
        "tema_id": "compartilhamento-de-infraestrutura",
        "tema_nome": "Compartilhamento de infraestrutura",
        "macrotema_sei": "Outorga de Distribuição",
        "temas_secundarios": [],
        "origem_classificacao": "direta",
        "atualizado_em": "2026-09-26T00:00:00Z"
    })
    
    theme = store.get_theme("Outorga de Distribuição: Compartilhamento de Infraestrutura")
    assert theme is not None
    assert theme.tema_id == "compartilhamento-de-infraestrutura"

def test_in_memory_store_get_theme(in_memory_store):
    theme = in_memory_store.get_theme("Outorga de Distribuição: Compartilhamento de Infraestrutura")
    assert theme is not None
    assert theme.tema_id == "compartilhamento-de-infraestrutura"

def test_http_get_theme_fallback(in_memory_store):
    app.dependency_overrides[get_theme_store] = lambda: in_memory_store
    client = TestClient(app)
    
    response = client.get("/internal/v1/process-classification/Tipo Inexistente")
    assert response.status_code == 200
    data = response.json()
    assert data["tema_id"] == "pendente-classificacao"
    assert data["tipo_processo"] == "Tipo Inexistente"

def test_http_get_theme_success(in_memory_store):
    app.dependency_overrides[get_theme_store] = lambda: in_memory_store
    client = TestClient(app)
    
    response = client.get("/internal/v1/process-classification/Outorga de Distribuição: Compartilhamento de Infraestrutura")
    assert response.status_code == 200
    data = response.json()
    assert data["tema_id"] == "compartilhamento-de-infraestrutura"
    assert data["tema_nome"] == "Compartilhamento de infraestrutura"
