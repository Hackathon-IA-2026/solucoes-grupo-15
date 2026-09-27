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
  document_id: string;
  processo_numero: string | null;
};

export type MatchedChunk = {
  document_version: string;
  excerpt: string;
  score: number;
  is_latest: boolean;
  // Indice real do chunk no documento (backend, issue #96): com
  // document_version, e a chave do voto de feedback (issues #82/#94).
  // O agrupamento face/matched_chunks em si e divergencia aberta na #93.
  chunk_index: number;
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

/**
 * O chunk de maior score entre os casados de um card: e o chunk que
 * poe o card na sua posicao, e e sobre ele que o voto de feedback do
 * card e registrado (issue #94). Empate: o primeiro da lista. Quando a
 * #93 trocar o card agrupado por um card por chunk, o chunk do card e o
 * proprio resultado e esta escolha deixa de existir.
 */
export function bestMatchedChunk(chunks: MatchedChunk[]): MatchedChunk | undefined {
  return chunks.reduce<MatchedChunk | undefined>(
    (best, chunk) => (best === undefined || chunk.score > best.score ? chunk : best),
    undefined,
  );
}

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
