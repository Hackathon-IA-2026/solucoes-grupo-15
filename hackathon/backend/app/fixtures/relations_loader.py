"""Leitura da fixture de relacoes demo (TB1 Ticket 5, issue #21).

``demo_relations.json`` e um arquivo de arestas declarado a mao,
marcado ``"provisional": true`` - nenhuma extracao de padrao textual
(regex/NER) roda aqui nem em nenhum outro lugar desta issue; tipo,
origem, estado e evidencia de cada aresta vem exatamente como o
arquivo declara. O backend e o unico modulo que le este arquivo.
"""

import json
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_FIXTURE_PATH = Path(__file__).parent / "demo_relations.json"


@dataclass(frozen=True)
class FixtureRelationEvidence:
    document_version: str
    locator: str


@dataclass(frozen=True)
class FixtureRelation:
    source_id: str
    source_kind: str
    target_id: str
    target_kind: str
    type: str
    origin: str
    status: str
    evidence: FixtureRelationEvidence | None


@dataclass(frozen=True)
class FixtureRelations:
    provisional: bool
    relations: list[FixtureRelation]


def load_demo_relations(path: Path = _DEFAULT_FIXTURE_PATH) -> FixtureRelations:
    raw = json.loads(path.read_text(encoding="utf-8"))
    relations = [
        FixtureRelation(
            source_id=rel["source_id"],
            source_kind=rel["source_kind"],
            target_id=rel["target_id"],
            target_kind=rel["target_kind"],
            type=rel["type"],
            origin=rel["origin"],
            status=rel["status"],
            evidence=(
                FixtureRelationEvidence(
                    document_version=rel["evidence"]["document_version"],
                    locator=rel["evidence"]["locator"],
                )
                if rel.get("evidence") is not None
                else None
            ),
        )
        for rel in raw["relations"]
    ]
    return FixtureRelations(
        provisional=raw.get("provisional", False),
        relations=relations,
    )
