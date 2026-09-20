"""Leitura do corpus de fixtures demo (TB1 Ticket 2, issue #18).

``demo_corpus.json`` e um corpus fictício, claramente marcado
``"provisional": true`` - nunca dado real (a entrega da Carolina, issue
#14, continua bloqueada). O backend e o unico modulo que le este
arquivo; o ``ai`` nunca le a fixture diretamente, so recebe o payload
que ``run_ingestion`` (app/routes/ingestions.py) monta a partir daqui.

Nenhuma regra de "chave explicita" (tipo + identificador oficial) e
aplicada aqui: ``family_id``/``document_version``/``version_date`` vem
exatamente como a fixture declara.
"""

import json
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_FIXTURE_PATH = Path(__file__).parent / "demo_corpus.json"


@dataclass(frozen=True)
class FixtureDocumentVersion:
    document_id: str
    document_version: str
    family_id: str
    version_date: str
    version_date_source: str
    document_type: str
    processo_numero: str | None
    text: str


@dataclass(frozen=True)
class FixtureCorpus:
    corpus_version: str
    provisional: bool
    documents: list[FixtureDocumentVersion]


def load_demo_corpus(path: Path = _DEFAULT_FIXTURE_PATH) -> FixtureCorpus:
    raw = json.loads(path.read_text(encoding="utf-8"))
    documents = [
        FixtureDocumentVersion(
            document_id=doc["document_id"],
            document_version=doc["document_version"],
            family_id=doc["family_id"],
            version_date=doc["version_date"],
            version_date_source=doc["version_date_source"],
            document_type=doc["document_type"],
            processo_numero=doc.get("processo_numero"),
            text=doc["text"],
        )
        for doc in raw["documents"]
    ]
    return FixtureCorpus(
        corpus_version=raw["corpus_version"],
        provisional=raw.get("provisional", False),
        documents=documents,
    )
