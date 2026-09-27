"""Os hits demo devem apontar para textos e ids presentes no catalogo F3."""

import json
import re
from pathlib import Path

from app.fixtures.loader import load_demo_corpus

HACKATHON_DIR = Path(__file__).resolve().parents[2]


def test_case1_search_hits_match_catalog_and_source_markdown() -> None:
    corpus = load_demo_corpus()
    documents = {doc.document_version: doc for doc in corpus.documents}
    search_path = HACKATHON_DIR / "ai/app/fixtures/search_fixtures.json"
    queries = json.loads(search_path.read_text(encoding="utf-8"))["queries"]

    for hits in queries.values():
        for hit in hits:
            document = documents[hit["document_version"]]
            assert hit["family_id"] == document.family_id
            assert " ".join(hit["excerpt"].split()) in " ".join(document.text.split())

    case1 = [doc for doc in corpus.documents if doc.family_id.startswith("case1-")]
    assert len(case1) == 10
    for document in case1:
        source = HACKATHON_DIR / "data/case-1-carolina-mmgd" / document.source_pdf_relpath.replace(
            ".pdf", ".md"
        )
        text = re.sub(r"<!--.*?-->", " ", source.read_text(encoding="utf-8"), flags=re.S)
        assert document.text in " ".join(text.split())
