import { useEffect, useState } from "react";
import { ArrowUpRight, CircleDot, Link2, Network } from "lucide-react";
import { Link } from "react-router-dom";

import { fetchGraph, GraphNodeNotFoundError, type Graph, type GraphEdge } from "../api/relations";

/**
 * Painel "Relações" egocêntrico de um salto (TB1 Ticket 5, issue #21).
 *
 * Reutilizável: recebe um ``nodeId`` (família ou processo) e busca
 * GET /v1/documents/{nodeId}/graph. Agrupa as arestas por ``type`` e
 * mostra o(s) vizinho(s) de cada grupo como link — família vai para
 * ``/documents/{id}``, processo vai para ``/processos/{id}`` (ver
 * api/relations.ts e api/processos.ts). "Recentrar" é simplesmente
 * navegar para a página do vizinho, que monta seu próprio
 * ``RelationsPanel`` centrado nele — sem grafo visual interativo
 * (SVG/canvas), uma lista agrupada com links já satisfaz "egocêntrico
 * de um salto, recentrável" (decisão u4-visualization).
 *
 * Usado tanto em FamilyPage (``nodeId={familyId}``) quanto em
 * ProcessoPage (``nodeId={processoId}``).
 */

type PanelState =
  | { kind: "loading" }
  | { kind: "result"; graph: Graph }
  | { kind: "not-found" }
  | { kind: "error" };

export function RelationsPanel({ nodeId }: { nodeId: string }) {
  const [state, setState] = useState<PanelState>({ kind: "loading" });

  useEffect(() => {
    setState({ kind: "loading" });
    fetchGraph(nodeId)
      .then((graph) => setState({ kind: "result", graph }))
      .catch((error: unknown) => {
        if (error instanceof GraphNodeNotFoundError) {
          setState({ kind: "not-found" });
        } else {
          setState({ kind: "error" });
        }
      });
  }, [nodeId]);

  return (
    <section className="relations-panel" aria-label="painel de relações">
      <h3><Network size={18} /> Relações</h3>
      <p className="relations-description">Vizinhança declarada de um salto.</p>
      {state.kind === "loading" && <p className="panel-status">Carregando relações...</p>}
      {state.kind === "not-found" && <p className="panel-status">Nó não encontrado no grafo de relações.</p>}
      {state.kind === "error" && <p className="panel-status">Não foi possível carregar as relações.</p>}
      {state.kind === "result" && state.graph.edges.length === 0 && (
        <p>Nenhuma relação registrada para este item.</p>
      )}
      {state.kind === "result" && state.graph.edges.length > 0 && (
        <RelationsGroups edges={state.graph.edges} />
      )}
    </section>
  );
}

function RelationsGroups({ edges }: { edges: GraphEdge[] }) {
  const groups = groupByType(edges);

  return (
    <>
      {Object.entries(groups).map(([type, groupEdges]) => (
        <div className="relation-group" key={type} aria-label={`relações do tipo ${type}`}>
          <h4><Link2 size={14} /> {formatRelationType(type)}</h4>
          <ul>
            {groupEdges.map((edge) => (
              <li key={`${edge.type}-${edge.neighbor_kind}-${edge.neighbor_id}`}>
                <CircleDot size={13} aria-hidden="true" />
                <div><NeighborLink edge={edge} /><span className="relation-status">{edge.origin}, {edge.status}</span>
                {edge.evidence && (
                  <span className="relation-evidence">Evidência: {edge.evidence.locator} ({edge.evidence.document_version})</span>
                )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </>
  );
}

function NeighborLink({ edge }: { edge: GraphEdge }) {
  const to =
    edge.neighbor_kind === "processo"
      ? `/processos/${encodeURIComponent(edge.neighbor_id)}`
      : `/documents/${encodeURIComponent(edge.neighbor_id)}`;
  return <Link to={to}>{edge.neighbor_id} <ArrowUpRight size={14} aria-hidden="true" /></Link>;
}

function formatRelationType(value: string) {
  return value.replaceAll("_", " ");
}

function groupByType(edges: GraphEdge[]): Record<string, GraphEdge[]> {
  const groups: Record<string, GraphEdge[]> = {};
  for (const edge of edges) {
    if (!groups[edge.type]) {
      groups[edge.type] = [];
    }
    groups[edge.type].push(edge);
  }
  return groups;
}

export default RelationsPanel;
