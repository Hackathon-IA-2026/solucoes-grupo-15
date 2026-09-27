"""Contrato do endpoint publico de busca (TB1 Ticket 3, issue #19).

Seam testado: POST /v1/search. Isola o ai via dependency override de
get_ai_client (fake deterministico com hits crus fixos - nunca chama o
ai real por HTTP) e roda contra um Postgres real de teste (container
Docker, ver tests/conftest.py), populado via ``run_ingestion``
(reaproveitada da issue #18) antes de cada teste, para que os IDs
usados nos hits fake existam no catalogo.

Issue #78: ``SearchResultOut`` representa agora um chunk plano — sem
agrupamento por familia. Cada hit do ai vira um card separado.
Ordem total obrigatoria: score desc, desempate por
(document_version, chunk_index).
"""

import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.clients.ai_client import (
    AiSearchHit,
    AiSearchResponse,
    IndexDocumentPayload,
    IndexReport,
    get_ai_client,
)
from app.db import Base, get_db_session, make_engine, make_session_factory
from app.fixtures.loader import load_demo_corpus
from app.main import create_app
from app.models import SearchExecution
from app.routes.ingestions import run_ingestion


class _SeedAiClient:
    """Fake deterministico usado so para popular o catalogo via
    run_ingestion antes de cada teste (mesmo padrao de test_ingestions.py).
    """

    def index(self, documents: list[IndexDocumentPayload]) -> list[IndexReport]:
        return [
            IndexReport(
                document_version=doc.document_version,
                extracted_text_locator=f"/data/documents/{doc.document_version}/extracted.txt",
                chunks_indexed=1,
                model_version="fixture-demo",
            )
            for doc in documents
        ]


class _FakeSearchAiClient:
    """Fake deterministico de AiClient.search - devolve hits crus fixos,
    nunca chama o ai real por HTTP.
    """

    def __init__(self, hits: list[AiSearchHit]) -> None:
        self._hits = hits

    def search(self, query: str, top_k: int | None = None) -> AiSearchResponse:
        hits = self._hits if top_k is None else self._hits[:top_k]
        return AiSearchResponse(hits=hits, model_version="fixture-demo")


def _client(database_url: str, hits: list[AiSearchHit]) -> TestClient:
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)

    def _override_session():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    _seed_catalog(session_factory)

    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: _FakeSearchAiClient(hits)
    app.dependency_overrides[get_db_session] = _override_session
    return TestClient(app)


def _seed_catalog(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        run_ingestion(load_demo_corpus(), ai_client=_SeedAiClient(), session=session)
        session.commit()


# ---------------------------------------------------------------------------
# Testes da forma de SearchResultOut (issue #78 — chunk plano)
# ---------------------------------------------------------------------------

def test_search_chunk_result_has_all_required_fields(database_url: str) -> None:
    """Cada resultado deve ter todos os campos do contrato chunk flat."""
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho na versao antiga",
            score=0.7,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    result = results[0]
    # Campos obrigatorios do contrato chunk flat
    assert result["family_id"] == "fam-auto-0007"
    assert result["document_version"] == "docver-auto-0007-v1"
    assert result["excerpt"] == "trecho na versao antiga"
    assert result["score"] == 0.7
    assert "localizador" in result  # pode ser str ou None
    assert result["document_type"] == "auto_de_infracao"
    assert result["document_id"] == "auto-0007"
    assert result["processo_numero"] == "48500.001234/2024-11"
    assert result["version_date"] == "2024-03-04"
    assert result["chunk_index"] == 0


def test_search_same_hit_twice_appears_twice(database_url: str) -> None:
    """O mesmo chunk devolvido duas vezes pelo ai aparece duas vezes — sem dedup."""
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho repetido",
            score=0.8,
        ),
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho repetido",
            score=0.8,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    # Ambos sao o mesmo document_version
    assert results[0]["document_version"] == "docver-auto-0007-v1"
    assert results[1]["document_version"] == "docver-auto-0007-v1"


def test_search_results_ordered_by_score_desc(database_url: str) -> None:
    """Resultado com score maior deve vir primeiro."""
    hits = [
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="score baixo",
            score=0.3,
        ),
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="score alto",
            score=0.9,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["score"] == 0.9
    assert results[1]["score"] == 0.3
    assert results[0]["document_version"] == "docver-auto-0007-v1"
    assert results[1]["document_version"] == "docver-defesa-0007-v1"


def test_search_deterministic_order_on_tie(database_url: str) -> None:
    """Mesmos scores: desempate por (document_version lexicografico, chunk_index)."""
    hits = [
        AiSearchHit(
            family_id="fam-norma-1000",
            document_version="docver-norma-1000-v1",
            excerpt="norma",
            score=0.5,
        ),
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="auto v1",
            score=0.5,
        ),
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="defesa",
            score=0.5,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "empate"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    # Todos com score 0.5 — desempate por document_version lexicografico
    doc_versions = [r["document_version"] for r in results]
    assert doc_versions == sorted(doc_versions), (
        "Desempate deterministico esperado: ordem lexicografica de document_version"
    )


def test_search_family_id_present_but_not_deduped(database_url: str) -> None:
    """family_id presente em cada resultado mas nao usado para colapsar."""
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="chunk 1 da mesma familia",
            score=0.8,
        ),
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="chunk outra familia",
            score=0.6,
        ),
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v2",
            excerpt="chunk 2 da mesma familia",
            score=0.4,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "sem dedup"})

    assert response.status_code == 200
    results = response.json()["results"]
    # Todos os 3 chunks aparecem — nao colapsa por family_id
    assert len(results) == 3
    family_ids = [r["family_id"] for r in results]
    assert family_ids.count("fam-auto-0007") == 2
    assert family_ids.count("fam-defesa-0007") == 1
    # family_id esta presente em cada resultado
    for result in results:
        assert "family_id" in result
        assert result["family_id"]


# ---------------------------------------------------------------------------
# Testes de envelope (adaptados da forma antiga)
# ---------------------------------------------------------------------------

def test_search_envelope_has_all_required_fields(database_url: str) -> None:
    hits = [
        AiSearchHit(
            family_id="fam-norma-1000",
            document_version="docver-norma-1000-v1",
            excerpt="trecho norma",
            score=0.8,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "qualquer consulta"})

    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "demo"
    assert body["corpus_version"] == "demo-v2-case1"
    assert body["model_version"] == "fixture-demo"
    assert body["ranking_version"] == "demo-ranking-v1"
    assert uuid.UUID(body["request_id"])


def test_search_request_id_is_unique_per_call(database_url: str) -> None:
    client = _client(database_url, hits=[])

    first = client.post("/v1/search", json={"query": "qualquer consulta"}).json()
    second = client.post("/v1/search", json={"query": "qualquer consulta"}).json()

    assert first["request_id"] != second["request_id"]


def test_search_returns_empty_results_and_full_envelope_when_ai_returns_no_hits(
    database_url: str,
) -> None:
    client = _client(database_url, hits=[])

    response = client.post("/v1/search", json={"query": "consulta sem correspondencia"})

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["data_mode"] == "demo"
    assert body["model_version"] == "fixture-demo"
    assert body["ranking_version"] == "demo-ranking-v1"
    assert body["corpus_version"] == "demo-v2-case1"
    assert uuid.UUID(body["request_id"])


def test_search_persists_a_search_execution_with_all_fields(database_url: str) -> None:
    """Seam 1 do Ticket 9 (issue #25): POST /v1/search grava SearchExecution.

    Confere que a linha criada tem todos os campos do contrato,
    incluindo os hits CRUS (antes de qualquer transformacao) e o envelope final
    serializado - insumos que app/replay.py::replay_search usa depois.
    """
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho na versao antiga",
            score=0.7,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "peca sobre auto de infracao"})
    body = response.json()

    session_factory = make_session_factory(make_engine(database_url))
    with session_factory() as session:
        execution = session.get(SearchExecution, body["request_id"])

    assert execution is not None
    assert execution.request_id == body["request_id"]
    assert execution.query == "peca sobre auto de infracao"
    assert execution.data_mode == body["data_mode"] == "demo"
    assert execution.corpus_version == body["corpus_version"]
    assert execution.model_version == body["model_version"]
    assert execution.ranking_version == body["ranking_version"]
    assert execution.code_reference  # Settings.code_reference: nao vazio, ver config.py
    assert execution.created_at is not None

    raw_hits = json.loads(execution.raw_hits_json)
    assert raw_hits == [
        {
            "family_id": "fam-auto-0007",
            "document_version": "docver-auto-0007-v1",
            "excerpt": "trecho na versao antiga",
            "score": 0.7,
        }
    ]
    assert json.loads(execution.response_json) == body


# ---------------------------------------------------------------------------
# Testes de data_mode dinamico (issue #69 — reconciliado com paginacao/#86)
# ---------------------------------------------------------------------------

def test_search_data_mode_is_real_when_embedder_is_bedrock(database_url: str, monkeypatch) -> None:
    """Issue #69: ``data_mode`` deixa de ser fixo em ``"demo"`` - reflete
    ``Settings.embedder`` (o mesmo toggle ``EMBEDDER`` do backend/ai).
    """
    from app.config import get_settings

    monkeypatch.setenv("EMBEDDER", "bedrock")
    get_settings.cache_clear()
    try:
        client = _client(database_url, hits=[])
        response = client.post("/v1/search", json={"query": "qualquer consulta"})
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["data_mode"] == "real"


def test_search_data_mode_real_is_preserved_across_cursor_continuation(
    database_url: str, monkeypatch
) -> None:
    """Issue #86: a continuacao por cursor devolve o ``data_mode`` congelado
    na primeira chamada (``execution.data_mode``), nao recalcula a partir do
    ``Settings.embedder`` corrente - mesmo se o toggle mudar entre as duas
    chamadas, a pagina 2 nao pode divergir da pagina 1.
    """
    from app.config import get_settings

    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho auto",
            score=0.9,
        ),
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="trecho defesa",
            score=0.7,
        ),
    ]
    monkeypatch.setenv("EMBEDDER", "bedrock")
    get_settings.cache_clear()
    try:
        client = _client(database_url, hits)
        first_resp = client.post(
            "/v1/search", json={"query": "data_mode real paginado", "limit": 1}
        )
        assert first_resp.status_code == 200
        first_body = first_resp.json()
        assert first_body["data_mode"] == "real"
        cursor = first_body["next_cursor"]
        assert cursor is not None

        # Muda o toggle antes da continuacao - a pagina 2 nao deve refletir isso.
        monkeypatch.setenv("EMBEDDER", "fake")
        get_settings.cache_clear()

        second_resp = client.post(
            "/v1/search", json={"query": "qualquer", "cursor": cursor, "limit": 1}
        )
    finally:
        get_settings.cache_clear()

    assert second_resp.status_code == 200
    assert second_resp.json()["data_mode"] == "real"


# ---------------------------------------------------------------------------
# Testes de paginacao lazy (issue #76)
# ---------------------------------------------------------------------------

def test_search_pagination_first_page_returns_next_cursor(database_url: str) -> None:
    """Primeira pagina com limit=1 sobre 2 chunks devolve next_cursor nao nulo."""
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho auto",
            score=0.9,
        ),
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="trecho defesa",
            score=0.7,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "paginacao primeira pagina", "limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["results"]) == 1
    # Primeiro resultado e o de maior score
    assert body["results"][0]["score"] == 0.9
    assert body["next_cursor"] is not None


def test_search_pagination_continuation_does_not_call_ai(database_url: str) -> None:
    """Continuacao com cursor valido nao chama AiClient.search.

    Verificado indiretamente: o FakeSearchAiClient da continuacao
    levantaria AssertionError se search() fosse chamado, pois
    passamos uma instancia sem hits. O resultado da segunda pagina
    deve conter o segundo chunk congelado na primeira chamada.
    """
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho auto",
            score=0.9,
        ),
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="trecho defesa",
            score=0.7,
        ),
    ]

    # Primeira chamada: obtemos o cursor
    engine = make_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = make_session_factory(engine)

    def _override_session():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    _seed_catalog(session_factory)

    # Cliente que falharia se search() fosse chamado numa segunda vez
    class _OnceAiClient:
        def __init__(self, hits: list[AiSearchHit]) -> None:
            self._hits = hits
            self._called = False

        def search(self, query: str, top_k: int | None = None) -> AiSearchResponse:
            assert not self._called, "AiClient.search foi chamado mais de uma vez — paginacao nao deveria chamar o ai"
            self._called = True
            return AiSearchResponse(hits=self._hits, model_version="fixture-demo")

    fake_ai = _OnceAiClient(hits)

    app = create_app()
    app.dependency_overrides[get_ai_client] = lambda: fake_ai
    app.dependency_overrides[get_db_session] = _override_session
    first_client = TestClient(app)

    first_resp = first_client.post("/v1/search", json={"query": "continuacao", "limit": 1})
    assert first_resp.status_code == 200
    first_body = first_resp.json()
    cursor = first_body["next_cursor"]
    assert cursor is not None

    # Segunda chamada (continuacao) - o mesmo TestClient/app com o mesmo fake_ai
    second_resp = first_client.post("/v1/search", json={"query": "qualquer", "cursor": cursor, "limit": 1})
    assert second_resp.status_code == 200
    second_body = second_resp.json()

    assert len(second_body["results"]) == 1
    # O segundo resultado ordenado por score e defesa-0007 (score 0.7)
    assert second_body["results"][0]["document_version"] == "docver-defesa-0007-v1"
    assert second_body["total"] == 2
    assert second_body["next_cursor"] is None


def test_search_pagination_invalid_cursor_returns_400(database_url: str) -> None:
    """Cursor invalido (nao decodificavel) deve retornar HTTP 400."""
    client = _client(database_url, hits=[])

    response = client.post(
        "/v1/search",
        json={"query": "qualquer", "cursor": "cursor-invalido-nao-base64-valido!!!"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "invalido" in detail.lower() or "invalid" in detail.lower()


def test_search_pagination_custom_limit(database_url: str) -> None:
    """Limit customizado e respeitado: limit=2 sobre 3 chunks devolve 2 resultados
    na primeira pagina e next_cursor nao nulo."""
    hits = [
        AiSearchHit(family_id="fam-auto-0007", document_version="docver-auto-0007-v1", excerpt="t1", score=0.9),
        AiSearchHit(family_id="fam-defesa-0007", document_version="docver-defesa-0007-v1", excerpt="t2", score=0.8),
        AiSearchHit(family_id="fam-decisao-0007", document_version="docver-decisao-0007-v1", excerpt="t3", score=0.7),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "limit customizado", "limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["results"]) == 2
    assert body["next_cursor"] is not None


def test_search_pagination_last_page_has_no_next_cursor(database_url: str) -> None:
    """Ultima pagina tem next_cursor nulo."""
    hits = [
        AiSearchHit(family_id="fam-auto-0007", document_version="docver-auto-0007-v1", excerpt="t1", score=0.9),
        AiSearchHit(family_id="fam-defesa-0007", document_version="docver-defesa-0007-v1", excerpt="t2", score=0.8),
    ]
    client = _client(database_url, hits)

    # Primeira pagina com limit=1 → cursor disponivel
    first_resp = client.post("/v1/search", json={"query": "ultima pagina", "limit": 1})
    assert first_resp.status_code == 200
    cursor = first_resp.json()["next_cursor"]
    assert cursor is not None

    # Segunda (e ultima) pagina → sem cursor
    second_resp = client.post("/v1/search", json={"query": "qualquer", "cursor": cursor, "limit": 1})
    assert second_resp.status_code == 200
    body = second_resp.json()
    assert len(body["results"]) == 1
    assert body["next_cursor"] is None
    assert body["total"] == 2


# ---------------------------------------------------------------------------
# Testes de replay (issue #77)
# ---------------------------------------------------------------------------

def test_replay_returns_recomputed_and_original_response(database_url: str) -> None:
    """Replay bem-sucedido devolve recomputed_response, original_response e matches."""
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho para replay",
            score=0.8,
        ),
    ]
    client = _client(database_url, hits)

    # Faz a busca original para ter um request_id persistido
    search_resp = client.post("/v1/search", json={"query": "consulta para replay"})
    assert search_resp.status_code == 200
    request_id = search_resp.json()["request_id"]

    # Chama o replay
    replay_resp = client.post(f"/v1/search/{request_id}/replay")
    assert replay_resp.status_code == 200

    body = replay_resp.json()
    assert body["request_id"] == request_id
    assert body["matches"] is True

    # recomputed_response e original_response devem ter os campos do SearchEnvelope
    for key in ("recomputed_response", "original_response"):
        envelope = body[key]
        assert envelope["request_id"] == request_id
        assert envelope["data_mode"] == "demo"
        assert envelope["model_version"] == "fixture-demo"
        assert envelope["ranking_version"] == "demo-ranking-v1"
        assert len(envelope["results"]) == 1
        # Chunk plano — tem document_version, nao matched_chunks
        assert envelope["results"][0]["document_version"] == "docver-auto-0007-v1"
        assert envelope["results"][0]["family_id"] == "fam-auto-0007"

    # Os dois envelopes devem ser iguais (matches True)
    assert body["recomputed_response"] == body["original_response"]


def test_replay_returns_404_for_unknown_request_id(database_url: str) -> None:
    """Replay com request_id inexistente deve retornar HTTP 404."""
    client = _client(database_url, hits=[])

    fake_id = str(uuid.uuid4())
    response = client.post(f"/v1/search/{fake_id}/replay")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert fake_id in detail


# ---------------------------------------------------------------------------
# Testes de corpus stale (issue #81)
# ---------------------------------------------------------------------------

def test_search_stale_corpus_false_on_first_call(database_url: str) -> None:
    """Primeira chamada sempre tem stale_corpus=False (corpus acabou de ser usado)."""
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="trecho qualquer",
            score=0.8,
        ),
    ]
    client = _client(database_url, hits)

    response = client.post("/v1/search", json={"query": "primeira chamada stale"})

    assert response.status_code == 200
    body = response.json()
    assert body["stale_corpus"] is False


def test_search_stale_corpus_false_on_continuation_with_same_corpus(
    database_url: str,
) -> None:
    """Continuacao com corpus inalterado tem stale_corpus=False."""
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="primeiro chunk",
            score=0.9,
        ),
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="segundo chunk",
            score=0.7,
        ),
    ]
    client = _client(database_url, hits)

    # Primeira pagina
    first_resp = client.post("/v1/search", json={"query": "corpus igual", "limit": 1})
    assert first_resp.status_code == 200
    first_body = first_resp.json()
    cursor = first_body["next_cursor"]
    assert cursor is not None

    # Continuacao — corpus nao mudou
    second_resp = client.post("/v1/search", json={"query": "qualquer", "cursor": cursor, "limit": 1})
    assert second_resp.status_code == 200
    second_body = second_resp.json()
    assert second_body["stale_corpus"] is False


def test_search_stale_corpus_true_on_continuation_after_corpus_update(
    database_url: str,
) -> None:
    """Continuacao apos corpus ter sido atualizado tem stale_corpus=True.

    Estrategia: faz a primeira busca normalmente, entao altera diretamente
    SearchExecution.corpus_version para uma versao mais antiga no banco,
    simulando que o catalogo foi atualizado apos a busca original. A
    continuacao deve detectar a divergencia e retornar stale_corpus=True.
    """
    hits = [
        AiSearchHit(
            family_id="fam-auto-0007",
            document_version="docver-auto-0007-v1",
            excerpt="chunk stale",
            score=0.9,
        ),
        AiSearchHit(
            family_id="fam-defesa-0007",
            document_version="docver-defesa-0007-v1",
            excerpt="chunk stale 2",
            score=0.7,
        ),
    ]
    client = _client(database_url, hits)

    # Primeira busca — obtem cursor e request_id
    first_resp = client.post("/v1/search", json={"query": "stale test", "limit": 1})
    assert first_resp.status_code == 200
    first_body = first_resp.json()
    request_id = first_body["request_id"]
    cursor = first_body["next_cursor"]
    assert cursor is not None

    # Altera SearchExecution.corpus_version para simular que o catalogo foi atualizado
    from app.db import make_engine, make_session_factory
    from app.models import SearchExecution as SE

    engine = make_engine(database_url)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        execution = session.get(SE, request_id)
        assert execution is not None
        execution.corpus_version = "corpus-version-antiga-stale"
        session.commit()

    # Continuacao — corpus_version do SearchExecution e mais antiga que a do catalogo
    second_resp = client.post("/v1/search", json={"query": "qualquer", "cursor": cursor, "limit": 1})
    assert second_resp.status_code == 200
    second_body = second_resp.json()
    assert second_body["stale_corpus"] is True
