"""Testes do carregador do corpus real do caso 1 (issue #69).

Nenhuma chamada de rede/AWS/Postgres - so leitura de arquivos locais
(demo_corpus.json + os .md committados em hackathon/data/case-1-carolina-mmgd/).
"""

from app.fixtures.case1_loader import (
    CASE1_REAL_CORPUS_VERSION,
    load_case1_real_corpus,
)


def test_loads_exactly_the_ten_case1_documents_with_full_markdown_text():
    corpus = load_case1_real_corpus()

    assert corpus.corpus_version == CASE1_REAL_CORPUS_VERSION
    assert len(corpus.documents) == 10
    assert all(doc.family_id.startswith("case1-") for doc in corpus.documents)
    # Curto resumo de demo tinha ~300-450 caracteres - o texto real e uma
    # extracao inteira de PDF, ordens de magnitude maior.
    assert all(len(doc.text) > 1000 for doc in corpus.documents)


def test_each_document_text_matches_its_source_markdown_file_verbatim():
    from pathlib import Path

    corpus = load_case1_real_corpus()
    # tests/test_case1_loader.py -> tests -> backend -> hackathon -> raiz do repo.
    repo_root = Path(__file__).resolve().parents[3]
    data_dir = repo_root / "hackathon" / "data" / "case-1-carolina-mmgd"

    for doc in corpus.documents:
        md_relpath = doc.source_pdf_relpath.rsplit(".pdf", 1)[0] + ".md"
        assert doc.text == (data_dir / md_relpath).read_text(encoding="utf-8")


def test_document_metadata_matches_the_case1_readme_processos():
    corpus = load_case1_real_corpus()

    processos = {doc.processo_numero for doc in corpus.documents}
    assert processos == {
        "48500.004024/2017-80",
        "48500.000639/2019-07",
        "48500.901433/2024-53",
        "48500.009907/2025-96",
        "48500.017555/2025-42",
    }
