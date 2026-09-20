/**
 * Cliente do frontend para a busca (TB1 Ticket 3, issue #19).
 *
 * Chama so POST /v1/search no backend (nunca o ai nem o indice vetorial
 * diretamente), conforme a fronteira de modulos decidida na arquitetura.
 * Os tipos abaixo espelham o envelope de resposta documentado em
 * hackathon/backend/app/routes/search.py.
 */

export type SearchFace = {
  document_version: string;
  version_date: string;
  document_type: string;
};

export type MatchedChunk = {
  document_version: string;
  excerpt: string;
  score: number;
  is_latest: boolean;
};

export type SearchResult = {
  family_id: string;
  face: SearchFace;
  matched_chunks: MatchedChunk[];
};

export type SearchEnvelope = {
  request_id: string;
  data_mode: string;
  corpus_version: string;
  model_version: string;
  ranking_version: string;
  results: SearchResult[];
};

export async function searchDocuments(query: string): Promise<SearchEnvelope> {
  const response = await fetch("/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error(`Busca falhou com status ${response.status}`);
  }

  return (await response.json()) as SearchEnvelope;
}
