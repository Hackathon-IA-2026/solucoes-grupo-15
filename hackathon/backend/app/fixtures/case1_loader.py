"""Carregador do corpus REAL do caso 1 (issue #69).

Reusa a identidade documental (``family_id``, ``document_version``,
``document_id``, ``version_date``, ``document_type``,
``processo_numero``, ``source_pdf_relpath``) ja curada em
``app/fixtures/demo_corpus.json`` para os 10 documentos ``"case1-*"``
(os mesmos 10 PDFs do caso 1, ver
``hackathon/data/case-1-carolina-mmgd/``) - mas substitui o ``text``
curto e resumido dessa fixture (so metadado/resumo de demonstracao, ver
o proprio campo ``"disclaimer"`` do arquivo: "nao ha embeddings, busca
vetorial ou conclusao juridica automatica") pelo texto Markdown REAL e
completo produzido pela extracao da issue #59
(``hackathon/data/case-1-carolina-mmgd/<processo>/<peca>.md``,
committado no repositorio - ver ``source_pdf_relpath`` de cada
documento, so troca a extensao ``.pdf`` por ``.md``).

``CASE1_REAL_CORPUS_VERSION`` identifica este corpus real (10
documentos, texto Markdown completo) - deliberadamente separado do
``corpus_version`` da fixture demo (``"demo-v2-case1"``, so resumos
curados de ~300-450 caracteres) mesmo reusando os mesmos
``family_id``/``document_version``. Rodar a ingestao real (ver
``hackathon/tools/case1_recall/seed_and_measure.py``) sobrescreve
``corpus_version``/``model_version``/``extracted_text_locator`` desses
10 ``document_version`` no catalogo para os valores reais - e a
transicao esperada de "demo" para "real" para este recorte, nunca um
bug: o catalogo sempre reflete o modo da ultima ingestao rodada para
aquele ``document_version``.

Interface estavel para a issue #73 (indexacao do corpus completo):
``load_case1_real_corpus`` devolve um ``FixtureCorpus`` comum (mesmo
tipo que ``load_demo_corpus``) - indexar um corpus maior e so trocar a
fonte dos documentos (outro loader, outro ``corpus_version``), nunca
mudar a forma consumida por ``run_ingestion``.
"""

from __future__ import annotations

from pathlib import Path

from app.fixtures.loader import FixtureCorpus, FixtureDocumentVersion, load_demo_corpus

CASE1_REAL_CORPUS_VERSION = "case1-real-v1"
CASE1_FAMILY_PREFIX = "case1-"
CASE1_EXPECTED_DOCUMENT_COUNT = 10

# app/fixtures/case1_loader.py -> fixtures -> app -> backend -> hackathon -> raiz do repo.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_CASE1_DATA_DIR = _REPO_ROOT / "hackathon" / "data" / "case-1-carolina-mmgd"


def load_case1_real_corpus(data_dir: Path = _DEFAULT_CASE1_DATA_DIR) -> FixtureCorpus:
    """Devolve o corpus real do caso 1: os mesmos 10 documentos
    ``"case1-*"`` da fixture demo, com o texto Markdown completo (nao o
    resumo curado de demonstracao).
    """
    demo = load_demo_corpus()
    case1_docs = [doc for doc in demo.documents if doc.family_id.startswith(CASE1_FAMILY_PREFIX)]
    if len(case1_docs) != CASE1_EXPECTED_DOCUMENT_COUNT:
        raise ValueError(
            f"Esperava {CASE1_EXPECTED_DOCUMENT_COUNT} documentos 'case1-*' em "
            f"demo_corpus.json, encontrou {len(case1_docs)} - a fixture demo mudou?"
        )

    documents = [_with_real_text(doc, data_dir) for doc in case1_docs]
    return FixtureCorpus(
        corpus_version=CASE1_REAL_CORPUS_VERSION,
        provisional=False,
        documents=documents,
    )


def _with_real_text(doc: FixtureDocumentVersion, data_dir: Path) -> FixtureDocumentVersion:
    if not doc.source_pdf_relpath:
        raise ValueError(
            f"Documento {doc.document_version!r} sem source_pdf_relpath - "
            "nao ha como localizar o Markdown real correspondente."
        )
    md_relpath = doc.source_pdf_relpath.rsplit(".pdf", 1)[0] + ".md"
    md_path = data_dir / md_relpath
    text = md_path.read_text(encoding="utf-8")
    return FixtureDocumentVersion(
        document_id=doc.document_id,
        document_version=doc.document_version,
        family_id=doc.family_id,
        version_date=doc.version_date,
        version_date_source=doc.version_date_source,
        document_type=doc.document_type,
        processo_numero=doc.processo_numero,
        text=text,
        source_pdf_relpath=doc.source_pdf_relpath,
    )
