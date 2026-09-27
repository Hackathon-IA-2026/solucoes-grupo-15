from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class ProcessClassification(BaseModel):
    tipo_processo: str
    tema_id: str
    tema_nome: str
    descricao: str = ""
    macrotema_sei: str
    temas_secundarios: List[str] = Field(default_factory=list)
    origem_classificacao: str = "direta"
    atualizado_em: str

class TemaTaxonomy(BaseModel):
    tema_id: str
    tema_nome: str
    descricao: str = ""
    tipos_processo: List[str] = Field(default_factory=list)
