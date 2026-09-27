"""Testes da rota publica GET /v1/themes."""

import pytest
from fastapi.testclient import TestClient

from app.clients.ai_client import AiClient, AiTheme, get_ai_client
from app.main import app


class FakeAiClientForThemes:
    def get_themes(self) -> list[AiTheme]:
        return [
            AiTheme(
                tema_id="transicao-energetica",
                tema_nome="Transição Energética",
                descricao="Fontes renováveis, descarbonização, hidrogênio e armazenamento.",
                tipos_processo=["Outorga de Geração: Hídrica - Autorização"],
            ),
            AiTheme(
                tema_id="tarifas-e-receitas-reguladas",
                tema_nome="Tarifas e receitas reguladas",
                descricao="Metodologia tarifária, reajustes periódicos e RAP.",
                tipos_processo=["Gestão Tarifária: Transmissão - Reajuste Anual da RAP"],
            ),
        ]


def test_list_themes_endpoint():
    app.dependency_overrides[get_ai_client] = lambda: FakeAiClientForThemes()
    client = TestClient(app)

    response = client.get("/v1/themes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "transicao-energetica"
    assert data[0]["name"] == "Transição Energética"
    assert data[0]["description"] == "Fontes renováveis, descarbonização, hidrogênio e armazenamento."
    assert "tipos_processo" in data[0]
    assert data[0]["status"] == "Disponível"
