import { Info } from "lucide-react";
import type { CSSProperties } from "react";

import type { ExploreData } from "../../types/product";

export function CoveragePanel({ data }: { data: ExploreData }) {
  return (
    <aside className="coverage-panel">
      <div className="coverage-heading"><h2>Visão geral da pesquisa</h2><button type="button" title="Indicadores derivados dos scores declarados na fixture"><Info size={17} /></button></div>
      <blockquote>{data.query}</blockquote>
      <section className="coverage-card">
        <h3>Cobertura da pesquisa</h3>
        <div className="coverage-summary"><div className="coverage-ring" style={{ "--coverage": `${data.coverage * 3.6}deg` } as CSSProperties}><strong>{data.coverage}%</strong></div><div><strong>Correspondência da fixture</strong><p>{data.coverageSummary}</p></div></div>
        <div className="coverage-metrics">{data.metrics.map((metric) => <div className="coverage-metric" key={metric.label}><div><span>{metric.label} <small>({metric.detail})</small></span><strong>{metric.value}%</strong></div><div className="metric-track"><span className={metric.tone} style={{ width: `${metric.value}%` }} /></div></div>)}</div>
      </section>
      <section className="gaps-card">
        <div className="gaps-heading"><h3>Limites desta pesquisa</h3><span>modo demo</span></div>
        <ol>{data.gaps.map((gap, index) => <li key={gap.id}><span>{index + 1}</span><div><strong>{gap.title}</strong><p>{gap.detail}</p></div></li>)}</ol>
      </section>
    </aside>
  );
}
