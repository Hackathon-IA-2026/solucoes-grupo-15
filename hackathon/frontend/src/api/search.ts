/**
 * Cliente do frontend para a busca (TB1 Ticket 3, issue #19; busca por
 * chunk e paginacao, issue #93).
 *
 * Chama so POST /v1/search no backend (nunca o ai nem o indice vetorial
 * diretamente), conforme a fronteira de modulos decidida na arquitetura.
 * Os tipos abaixo espelham ``SearchResultOut``/``SearchEnvelope`` de
 * hackathon/backend/app/routes/search.py: desde a issue #78 cada
 * resultado e um chunk casado, plano, sem agrupamento por familia
 * (``family_id`` segue so como dado). ``(document_version, chunk_index)``
 * identifica o chunk (issue #96) e e a chave do voto de feedback (#82/#94).
 */

import { apiFetch } from "./client";

export type SearchResult = {
  family_id: string;
  document_version: string;
  chunk_id: string;
  chunk_index: number;
  excerpt: string;
  score: number;
  localizador: string | null;
  document_type: string;
  document_id: string;
  processo_numero: string | null;
  version_date: string;
};

export type SearchEnvelope = {
  request_id: string;
  data_mode: string;
  corpus_version: string;
  model_version: string;
  ranking_version: string;
  results: SearchResult[];
  // Numero de chunks do conjunto congelado inteiro, nao so desta pagina (#76).
  total: number;
  // Cursor opaco da proxima pagina; nulo na ultima (#76).
  next_cursor: string | null;
  // true quando ja existe corpus_version mais novo que o desta busca (#79).
  stale_corpus: boolean;
};

/**
 * Sem ``cursor``: executa a busca (o backend chama o ai uma unica vez e
 * congela o conjunto ordenado). Com ``cursor`` (o ``next_cursor`` da
 * pagina anterior): devolve a proxima pagina do mesmo conjunto congelado,
 * sem nova chamada ao ai (issue #76). O backend exige ``query`` tambem
 * na continuacao; o tamanho da pagina fica no default do backend (10,
 * u4-visualization).
 */
export async function searchDocuments(query: string, cursor?: string): Promise<SearchEnvelope> {
  const response = await apiFetch("/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cursor === undefined ? { query } : { query, cursor }),
  });

  if (!response.ok) {
    throw new Error(`Busca falhou com status ${response.status}`);
  }

  return (await response.json()) as SearchEnvelope;
}

/**
 * Acrescenta a pagina seguinte ao fim do conjunto ja carregado: os
 * resultados anteriores nunca mudam de posicao (u4-visualization,
 * issue-28). ``next_cursor``/``total``/``stale_corpus`` passam a ser os
 * da pagina mais recente.
 */
export function appendSearchPage(loaded: SearchEnvelope, next: SearchEnvelope): SearchEnvelope {
  return {
    ...loaded,
    results: [...loaded.results, ...next.results],
    total: next.total,
    next_cursor: next.next_cursor,
    stale_corpus: loaded.stale_corpus || next.stale_corpus,
  };
}
