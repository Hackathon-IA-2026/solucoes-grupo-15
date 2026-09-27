import { ArrowRight, FileText, RefreshCw, Search, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { PageHero } from "../components/layout/PageHero";
import { appRepository } from "../services/appRepository";
import type { Family } from "../types/product";

type State = { kind: "loading" } | { kind: "ready"; families: Family[] } | { kind: "error" };

export function FamiliesPage() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [query, setQuery] = useState("");

  function load() {
    setState({ kind: "loading" });
    appRepository.getFamilies()
      .then((families) => setState({ kind: "ready", families }))
      .catch(() => setState({ kind: "error" }));
  }

  useEffect(load, []);

  const visible = useMemo(() => state.kind === "ready"
    ? state.families.filter((family) => `${family.name} ${family.description}`.toLocaleLowerCase("pt-BR").includes(query.toLocaleLowerCase("pt-BR")))
    : [], [state, query]);

  return (
    <div className="product-page">
      <PageHero icon={Sparkles} title="Famílias documentais" description="Peças e versões disponíveis no catálogo demonstrativo." />
      <div className="page-toolbar">
        <div className="toolbar-search"><Search size={18} /><input aria-label="Pesquisar famílias" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Pesquisar documento ou processo..." /></div>
      </div>
      {state.kind === "loading" && <div className="family-grid">{[1, 2, 3, 4].map((item) => <div className="skeleton family-skeleton" key={item} />)}</div>}
      {state.kind === "error" && <div className="product-empty"><FileText size={28} /><h3>Não foi possível carregar as famílias.</h3><button className="yellow-button" type="button" onClick={load}><RefreshCw size={17} /> Tentar novamente</button></div>}
      {state.kind === "ready" && (visible.length === 0
        ? <div className="product-empty"><Sparkles size={28} /><h3>Nenhuma família encontrada.</h3><p>Tente outro documento ou processo.</p></div>
        : <div className="family-grid">{visible.map((family) => <article className={`family-card family-${family.tone}`} key={family.id}>
          <div className="family-visual"><span><FileText size={29} /></span></div>
          <div className="family-body"><h2>{family.name}</h2><p>{family.description}</p><span className="family-status">{family.status}</span><footer><span>{family.documents} versão(ões)</span><Link to={`/documents/${encodeURIComponent(family.id)}`}>Abrir documento <ArrowRight size={16} /></Link></footer></div>
        </article>)}</div>)}
    </div>
  );
}
