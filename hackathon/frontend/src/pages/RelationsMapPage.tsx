import { FileText, Network, RefreshCw, Search, Waypoints } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchFamilies } from "../api/documents";
import { fetchProcessos } from "../api/processos";
import { fetchGraph } from "../api/relations";
import { PageHero } from "../components/layout/PageHero";

type Node = { id: string; label: string; kind: "processo" | "family"; detail: string; position: string };
type State = { kind: "loading" } | { kind: "ready"; nodes: Node[] } | { kind: "error" };
const positions = ["top-left", "bottom-left", "top-right", "bottom-right"];

export function RelationsMapPage() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [selectedId, setSelectedId] = useState("");
  const [query, setQuery] = useState("");

  function load() {
    setState({ kind: "loading" });
    Promise.all([fetchProcessos(), fetchFamilies()])
      .then(async ([processes, families]) => {
        if (processes.length === 0) return [];
        const process = processes[0];
        const graph = await fetchGraph(process.processo_id);
        const names = new Map(families.map((family) => [family.family_id, family.document_id]));
        return [
          { id: process.processo_id, label: process.processo_id, kind: "processo" as const, detail: `${process.pieces_count} peças documentais`, position: "center" },
          ...graph.edges.map((edge, index) => ({
            id: edge.neighbor_id,
            label: names.get(edge.neighbor_id) ?? edge.neighbor_id,
            kind: edge.neighbor_kind,
            detail: edge.type,
            position: positions[index % positions.length],
          })),
        ];
      })
      .then((nodes) => { setState({ kind: "ready", nodes }); setSelectedId(nodes[0]?.id ?? ""); })
      .catch(() => setState({ kind: "error" }));
  }

  useEffect(load, []);

  const nodes = state.kind === "ready" ? state.nodes : [];
  const visible = nodes.filter((node) => `${node.label} ${node.detail}`.toLocaleLowerCase("pt-BR").includes(query.toLocaleLowerCase("pt-BR")));
  const selected = nodes.find((node) => node.id === selectedId);

  return (
    <div className="product-page">
      <PageHero icon={Network} title="Mapas e Relações" description="Relações declaradas no catálogo documental do processo mais recente." />
      <div className="page-toolbar"><div className="toolbar-search"><Search size={18} /><input aria-label="Buscar no mapa" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar processo ou documento..." /></div></div>
      {state.kind === "loading" && <div className="skeleton wide" />}
      {state.kind === "error" && <div className="product-empty"><h3>Não foi possível carregar o grafo.</h3><button type="button" onClick={load}><RefreshCw size={17} /> Tentar novamente</button></div>}
      {state.kind === "ready" && (nodes.length === 0
        ? <div className="product-empty"><h3>Nenhum processo disponível.</h3></div>
        : <div className="relations-layout"><section className="relation-canvas" aria-label="Mapa de relações do processo"><div className="relation-orbit" aria-hidden="true" />{visible.map((node) => {
          const Icon = node.kind === "processo" ? Waypoints : FileText;
          return <button type="button" key={node.id} className={`relation-node ${node.position} ${selectedId === node.id ? "selected" : ""}`} onClick={() => setSelectedId(node.id)}><Icon size={20} /><span><strong>{node.label}</strong><small>{node.kind === "processo" ? "Processo" : "Documento"}</small></span></button>;
        })}</section><aside className="summary-sidebar relation-detail">{selected && <><p className="page-kicker">Item selecionado</p><h2>{selected.label}</h2><span className="status-chip blue">{selected.kind === "processo" ? "Processo" : "Documento"}</span><p>{selected.detail}</p><Link className="yellow-button" to={selected.kind === "processo" ? `/processos/${encodeURIComponent(selected.id)}` : `/documents/${encodeURIComponent(selected.id)}`}>Ver detalhes</Link></>}</aside></div>)}
    </div>
  );
}
