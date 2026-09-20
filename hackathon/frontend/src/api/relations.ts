/**
 * Cliente do frontend para o grafo de relacoes (TB1 Ticket 5, issue #21).
 *
 * Chama so GET /v1/documents/{nodeId}/graph no backend (nunca o ai nem
 * o indice vetorial diretamente). ``nodeId`` pode ser um ``family_id``
 * ou o ``id`` (numero SEI) de um processo - o backend resolve qual e
 * qual (ver hackathon/backend/app/routes/relations.py). Um numero de
 * processo real contem "/" (ex. "48500.001234/2024-11"); por isso
 * ``nodeId`` sempre passa por ``encodeURIComponent`` antes de entrar na
 * URL, e o backend usa o conversor ``:path`` do Starlette para aceitar
 * o "/" decodificado.
 */

export type NodeKind = "family" | "processo";

export type RelationEvidence = {
  document_version: string;
  locator: string;
};

export type GraphEdge = {
  type: string;
  origin: string;
  status: string;
  neighbor_id: string;
  neighbor_kind: NodeKind;
  evidence: RelationEvidence | null;
};

export type Graph = {
  node_id: string;
  node_kind: NodeKind;
  edges: GraphEdge[];
};

/**
 * Sinaliza especificamente o 404 de "no nao encontrado", para o painel
 * distinguir esse caso (mensagem clara) de uma falha de rede generica.
 */
export class GraphNodeNotFoundError extends Error {}

export async function fetchGraph(nodeId: string): Promise<Graph> {
  const response = await fetch(`/v1/documents/${encodeURIComponent(nodeId)}/graph`);

  if (response.status === 404) {
    throw new GraphNodeNotFoundError("Nó não encontrado");
  }
  if (!response.ok) {
    throw new Error(`Consulta de grafo falhou com status ${response.status}`);
  }

  return (await response.json()) as Graph;
}
