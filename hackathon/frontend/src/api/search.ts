/**
 * Cliente do frontend para a busca (TB1 Ticket 3, issue #19).
 *
 * Chama so POST /v1/search no backend (nunca o ai nem o indice vetorial
 * diretamente), conforme a fronteira de modulos decidida na arquitetura.
 * Os tipos abaixo espelham o envelope de resposta documentado em
 * hackathon/backend/app/routes/search.py.
 */

import { apiFetch } from "./client";

export type MatchedChunk = {
  document_version: string;
  excerpt: string;
  score: number;
};

export type SearchResult = MatchedChunk & {
  family_id: string;
  localizador: string | null;
  document_type: string;
  document_id: string;
  processo_numero: string | null;
  version_date: string;
  chunk_index: number;
};

export type SearchEnvelope = {
  request_id: string;
  data_mode: string;
  corpus_version: string;
  model_version: string;
  ranking_version: string;
  results: SearchResult[];
  total: number;
  next_cursor: string | null;
  stale_corpus: boolean;
};

export async function searchDocuments(query: string): Promise<SearchEnvelope> {
  const response = await apiFetch("/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error(`Busca falhou com status ${response.status}`);
  }

  return (await response.json()) as SearchEnvelope;
}
