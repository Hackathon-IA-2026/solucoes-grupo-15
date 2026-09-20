"""Replay deterministico de uma busca registrada (TB1 Ticket 9, issue #25).

Decisao fechada i7-reproducibility
(requirements/perspec-me/capiwatt-lens-hackathon/concerns/i7-reproducibility.md):
"Reexecutar significa rodar novamente a recuperacao e o ranking sobre o
corpus preservado, usando o vetor da consulta registrada; consultar a
resposta salva nao satisfaz esse requisito." Nesta fase demo (sem
embeddings reais), "o vetor da consulta preservado" e os hits CRUS que
o ai devolveu para aquela busca (``SearchExecution.raw_hits_json``,
gravado em app/routes/search.py::_persist_search_execution ANTES do
agrupamento por familia).

``replay_search`` recomputa o agrupamento por familia (reusa
``_group_by_family`` de app/routes/search.py - o mesmo codigo que a
rota usa, para nao duplicar a logica) a partir desses hits crus
preservados e do catalogo ATUAL do Postgres (reflete o estado do
catalogo no momento do replay, nao um catalogo congelado no passado -
o corpus documental em si e "preservado" por ser o mesmo Postgres,
nao por um snapshot separado nesta fase demo). Os demais identificadores
do envelope (``data_mode``, ``corpus_version``, ``model_version``,
``ranking_version``) NAO sao recomputados - sao remontados a partir do
que ja foi registrado em ``SearchExecution``, pois sao identificadores
da execucao original, nao valores derivados do catalogo atual.

Esta funcao NUNCA chama ``AiClient`` nem faz nenhuma requisicao de
rede/IA - a propria assinatura (``request_id: str, session: Session``)
ja impede isso estruturalmente: nao ha nenhum parametro por onde
injetar um cliente ai. Prova o contrato de reprodutibilidade (#9)
sustentando reexecucao offline.
"""

import json
import sys
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.clients.ai_client import AiSearchHit
from app.models import SearchExecution
from app.routes.search import SearchEnvelope, _group_by_family


class SearchExecutionNotFound(Exception):
    """Nenhuma ``SearchExecution`` foi encontrada para o ``request_id`` pedido."""

    def __init__(self, request_id: str) -> None:
        super().__init__(f"Nenhuma search_execution encontrada para request_id={request_id!r}")
        self.request_id = request_id


@dataclass(frozen=True)
class ReplayResult:
    request_id: str
    recomputed_response: SearchEnvelope
    original_response: SearchEnvelope
    matches: bool


def replay_search(request_id: str, session: Session) -> ReplayResult:
    """Reexecuta, sem rede nem IA, a busca registrada sob ``request_id``.

    Busca a linha de ``SearchExecution`` (erro claro via
    ``SearchExecutionNotFound`` se nao existir), desserializa
    ``raw_hits_json`` de volta para ``AiSearchHit`` e reusa
    ``_group_by_family`` contra o catalogo atual (``session``) para
    recomputar os resultados agrupados. Remonta o envelope recomputado
    com os identificadores ja registrados (``data_mode``,
    ``corpus_version``, ``model_version``, ``ranking_version``) e
    devolve, junto, a resposta originalmente persistida e um booleano
    ``matches`` comparando as duas.
    """
    execution = session.get(SearchExecution, request_id)
    if execution is None:
        raise SearchExecutionNotFound(request_id)

    raw_hits = [AiSearchHit(**hit) for hit in json.loads(execution.raw_hits_json)]
    results, _current_corpus_version = _group_by_family(raw_hits, session)

    recomputed_response = SearchEnvelope(
        request_id=execution.request_id,
        data_mode=execution.data_mode,
        corpus_version=execution.corpus_version,
        model_version=execution.model_version,
        ranking_version=execution.ranking_version,
        results=results,
    )
    original_response = SearchEnvelope.model_validate_json(execution.response_json)

    return ReplayResult(
        request_id=request_id,
        recomputed_response=recomputed_response,
        original_response=original_response,
        matches=recomputed_response == original_response,
    )


def _main() -> None:
    from app.config import get_settings
    from app.db import make_engine, make_session_factory

    if len(sys.argv) != 2:
        print("uso: python -m app.replay <request_id>", file=sys.stderr)
        raise SystemExit(2)

    request_id = sys.argv[1]
    engine = make_engine(get_settings().database_url)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        try:
            result = replay_search(request_id, session)
        except SearchExecutionNotFound as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc

    print(f"request_id: {result.request_id}")
    print(f"matches: {result.matches}")
    print("recomputed_response:")
    print(result.recomputed_response.model_dump_json(indent=2))
    if not result.matches:
        print("original_response:")
        print(result.original_response.model_dump_json(indent=2))


if __name__ == "__main__":
    _main()
