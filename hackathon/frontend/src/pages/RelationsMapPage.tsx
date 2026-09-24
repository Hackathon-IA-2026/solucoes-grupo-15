import { FileText, Gavel, Network, Scale, Search, Waypoints } from "lucide-react";
import { useState } from "react";

import { PageHero } from "../components/layout/PageHero";

const nodes = [
  { id: "process", label: "48500.901433/2024-53", kind: "Processo principal", detail: "Fiscalização do atendimento a solicitações de conexão de MMGD.", icon: Waypoints, position: "center" },
  { id: "ai", label: "Auto de Infração 0035/2025", kind: "Documento", detail: "Registra as infrações fiscalizadas e a penalidade inicial.", icon: FileText, position: "top-left" },
  { id: "recurso", label: "Recurso administrativo", kind: "Documento", detail: "Argumentos apresentados pela distribuidora contra a autuação.", icon: Scale, position: "bottom-left" },
  { id: "voto", label: "Voto da Diretoria", kind: "Decisão", detail: "Fundamentos e conclusão submetidos à deliberação colegiada.", icon: Gavel, position: "top-right" },
  { id: "norma", label: "PRODIST · Módulo 3", kind: "Norma relacionada", detail: "Regras sobre acesso, conexão e prazos aplicáveis ao caso.", icon: FileText, position: "bottom-right" },
];

export function RelationsMapPage() {
  const [selected, setSelected] = useState(nodes[0]);
  const [query, setQuery] = useState("");
  const visible = nodes.filter((node) => `${node.label} ${node.kind}`.toLowerCase().includes(query.toLowerCase()));
  return (
    <div className="product-page"><PageHero icon={Network} title="Mapas e Relações" description="Visualize como processos, documentos, decisões e normas se conectam." />
      <div className="page-toolbar"><div className="toolbar-search"><Search size={18} /><input aria-label="Buscar no mapa" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar processo, documento ou norma..." /></div></div>
      <div className="relations-layout"><section className="relation-canvas" aria-label="Mapa de relações do processo"><div className="relation-orbit" aria-hidden="true" />{visible.map((node) => { const Icon = node.icon; return <button type="button" key={node.id} className={`relation-node ${node.position} ${selected.id === node.id ? "selected" : ""}`} onClick={() => setSelected(node)}><Icon size={20} /><span><strong>{node.label}</strong><small>{node.kind}</small></span></button>; })}</section><aside className="summary-sidebar relation-detail"><p className="page-kicker">Item selecionado</p><h2>{selected.label}</h2><span className="status-chip blue">{selected.kind}</span><p>{selected.detail}</p><h3>Relações confirmadas</h3><ul><li>pertence ao processo principal</li><li>citado em documento decisório</li><li>relação declarativa do catálogo</li></ul><button className="yellow-button" type="button"><FileText size={17} /> Ver detalhes</button></aside></div>
    </div>
  );
}
