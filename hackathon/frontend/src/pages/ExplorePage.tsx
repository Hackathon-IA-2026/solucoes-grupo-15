import { ArrowRight, BarChart3, FileSearch, Files, Info, Network, Search, Sparkles, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import { ExploreLanding } from "../components/explore/ExploreLanding";
import { CoveragePanel } from "../components/explore/CoveragePanel";
import { RankingCard } from "../components/explore/RankingCard";
import { mockExploreData } from "../mocks/explorar";
import { appRepository } from "../services/appRepository";
import type { ExploreData, RankedPrecedent } from "../types/product";

type ExploreState = { kind: "idle" } | { kind: "loading" } | { kind: "result"; data: ExploreData } | { kind: "error" };
const tabs = ["Resultados e ranking", "Lacunas da pesquisa", "Análise por tema", "Documentos relacionados"] as const;

export function ExplorePage() {
  const [params] = useSearchParams();
  const requestedQuery = params.get("q")?.trim() ?? "";
  const [query, setQuery] = useState(requestedQuery);
  const [activeFilter, setActiveFilter] = useState("Todos");
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>(tabs[0]);
  const [state, setState] = useState<ExploreState>(requestedQuery ? { kind: "loading" } : { kind: "idle" });
  const [fillingGaps, setFillingGaps] = useState(false);
  const [explainerOpen, setExplainerOpen] = useState(false);
  const [documentProcess, setDocumentProcess] = useState<RankedPrecedent | null>(null);

  function runSearch(searchQuery: string) {
    const normalized = searchQuery.trim();
    if (!normalized) {
      setState({ kind: "idle" });
      return;
    }
    setState({ kind: "loading" });
    appRepository.searchPrecedents(normalized).then((data) => setState({ kind: "result", data })).catch(() => setState({ kind: "error" }));
  }

  useEffect(() => {
    setQuery(requestedQuery);
    if (requestedQuery) runSearch(requestedQuery);
    else setState({ kind: "idle" });
  }, [requestedQuery]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    runSearch(query);
  }

  async function fillGaps() {
    setFillingGaps(true);
    try { setState({ kind: "result", data: await appRepository.findGapEvidence() }); }
    finally { setFillingGaps(false); }
  }

  const data = state.kind === "result" ? state.data : null;

  return (
    <div className={`explore-page ${state.kind === "idle" ? "explore-page-idle" : ""}`}>
      <header className="explore-hero">
        <p className="page-kicker"><Sparkles size={15} /> Inteligência regulatória</p>
        <h1>Explorar</h1><p>Encontre precedentes, normas e interpretações para embasar sua atuação regulatória.</p>
        <form className="explore-search" onSubmit={submit}>
          <Search size={21} />
          <input aria-label="Consulta de precedentes" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ex.: precedentes sobre conexão de MMGD" />
          <button className="yellow-button" type="submit" disabled={!query.trim()}>Buscar</button>
        </form>
        <div className="filter-row">{mockExploreData.filters.map((filter) => <button type="button" key={filter} className={activeFilter === filter ? "active" : ""} onClick={() => setActiveFilter(filter)}>{filter}</button>)}</div>
      </header>

      {state.kind === "idle" && <ExploreLanding />}
      {state.kind !== "idle" && <nav className="explore-tabs" aria-label="Visões da pesquisa">{tabs.map((tab) => <button type="button" key={tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)}>{tab}</button>)}</nav>}
      {state.kind === "loading" && <ExploreSkeleton />}
      {state.kind === "error" && <section className="product-error"><FileSearch size={28} /><h2>Não foi possível carregar os dados.</h2><button type="button" onClick={() => runSearch(query)}>Tentar novamente</button></section>}
      {data && (
        <div className="explore-layout">
          <section className="ranking-panel">
            <div className="panel-heading"><div><h2>{activeTab}</h2><p>{tabDescription(activeTab)}</p></div><button className="outline-button" type="button" onClick={() => setExplainerOpen(true)}><Info size={16} /> Como o ranking é calculado?</button></div>
            {activeTab === "Resultados e ranking" && <div className="ranking-list">{data.results.map((result) => <RankingCard key={result.processNumber} result={result} onOpenDocuments={setDocumentProcess} />)}</div>}
            {activeTab === "Lacunas da pesquisa" && <div className="tab-grid">{data.gaps.map((gap) => <article className="analysis-card" key={gap.id}><FileSearch size={22} /><h3>{gap.title}</h3><p>{gap.detail}</p><button type="button" onClick={fillGaps}>Buscar evidências <ArrowRight size={16} /></button></article>)}</div>}
            {activeTab === "Análise por tema" && <div className="tab-grid">{data.metrics.map((metric) => <article className="analysis-card" key={metric.label}><BarChart3 size={22} /><h3>{metric.label}</h3><strong>{metric.value}%</strong><p>Cobertura de {metric.detail} na pesquisa atual.</p></article>)}</div>}
            {activeTab === "Documentos relacionados" && <div className="tab-grid">{data.results.slice(0, 3).map((result) => <article className="analysis-card" key={result.processNumber}><Network size={22} /><h3>{result.processNumber}</h3><p>{result.documents.map((document) => document.label).join(" · ")}</p><button type="button" onClick={() => setDocumentProcess(result)}>Abrir conjunto <ArrowRight size={16} /></button></article>)}</div>}
          </section>
          <CoveragePanel data={data} fillingGaps={fillingGaps} onFillGaps={fillGaps} />
        </div>
      )}
      {explainerOpen && <div className="product-modal-backdrop" role="presentation" onMouseDown={() => setExplainerOpen(false)}><section className="product-modal" role="dialog" aria-modal="true" aria-labelledby="ranking-explainer-title" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" type="button" onClick={() => setExplainerOpen(false)} aria-label="Fechar"><X /></button><Info size={28} /><h2 id="ranking-explainer-title">Como o ranking é calculado?</h2><p>Nesta versão, o ranking é demonstrativo. Ele combina critérios definidos para validar a experiência antes da integração com inteligência real.</p><div className="criteria-grid">{["Aderência temática", "Similaridade jurídica", "Mesmo tipo de fiscalização", "Presença de decisão", "Recência", "Órgão e agente", "Documentos disponíveis", "Relevância regulatória"].map((item) => <span key={item}>{item}</span>)}</div></section></div>}
      {documentProcess && <div className="product-modal-backdrop" role="presentation" onMouseDown={() => setDocumentProcess(null)}><section className="product-modal documents-modal" role="dialog" aria-modal="true" aria-labelledby="documents-title" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" type="button" onClick={() => setDocumentProcess(null)} aria-label="Fechar"><X /></button><Files size={28} /><h2 id="documents-title">Documentos-chave</h2><p>Processo SEI {documentProcess.processNumber}</p><div className="document-list">{documentProcess.documents.map((document) => <button type="button" key={document.id}><FileSearch size={19} /><span><strong>{document.label}</strong><small>PDF disponível no corpus demonstrativo</small></span><ArrowRight size={17} /></button>)}</div></section></div>}
    </div>
  );
}

function ExploreSkeleton() {
  return <div className="explore-layout loading-layout" aria-label="Carregando ranking"><section className="ranking-panel"><div className="skeleton wide" />{[1, 2, 3, 4].map((item) => <div className="skeleton card" key={item} />)}</section><aside className="coverage-panel"><div className="skeleton wide" /><div className="skeleton tall" /></aside></div>;
}

function tabDescription(tab: (typeof tabs)[number]) {
  if (tab === "Resultados e ranking") return "Precedentes ranqueados por relevância para seu objetivo, com justificativas e documentos-chave.";
  if (tab === "Lacunas da pesquisa") return "Aspectos ainda pouco representados no conjunto de evidências.";
  if (tab === "Análise por tema") return "Cobertura jurídica, regulatória, técnica e econômica.";
  return "Conjuntos documentais associados aos precedentes prioritários.";
}
