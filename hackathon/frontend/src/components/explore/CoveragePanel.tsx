import { ArrowRight, CheckCircle2, Info, Search } from "lucide-react";
import type { CSSProperties } from "react";

import type { ExploreData } from "../../types/product";

export function CoveragePanel({ data, fillingGaps, onFillGaps }: { data: ExploreData; fillingGaps: boolean; onFillGaps: () => void }) {
  return (
    <aside className="coverage-panel">
      <div className="coverage-heading"><h2>Visão geral da pesquisa</h2><button type="button" title="Cobertura baseada em critérios mockados"><Info size={17} /></button></div>
      <blockquote>{data.query}</blockquote>
      <section className="coverage-card">
        <h3>Cobertura da pesquisa</h3>
        <div className="coverage-summary"><div className="coverage-ring" style={{ "--coverage": `${data.coverage * 3.6}deg` } as CSSProperties}><strong>{data.coverage}%</strong></div><div><strong>{data.coverage >= 85 ? "Ótima cobertura geral" : "Boa cobertura geral"}</strong><p>{data.coverageSummary}</p></div></div>
        <div className="coverage-metrics">{data.metrics.map((metric) => <div className="coverage-metric" key={metric.label}><div><span>{metric.label} <small>({metric.detail})</small></span><strong>{metric.value}%</strong></div><div className="metric-track"><span className={metric.tone} style={{ width: `${metric.value}%` }} /></div></div>)}</div>
      </section>
      <section className="gaps-card">
        <div className="gaps-heading"><h3>Lacunas identificadas</h3><span>{data.gaps.filter((gap) => !gap.resolved).length} relevantes</span></div>
        <ol>{data.gaps.map((gap, index) => <li className={gap.resolved ? "resolved" : ""} key={gap.id}><span>{gap.resolved ? <CheckCircle2 size={18} /> : index + 1}</span><div><strong>{gap.title}</strong><p>{gap.resolved ? "Nova evidência encontrada e incorporada à cobertura." : gap.detail}</p></div></li>)}</ol>
      </section>
      <button className="fill-gaps-button" type="button" onClick={onFillGaps} disabled={fillingGaps}>{fillingGaps ? <span className="button-spinner" /> : <Search size={18} />} {fillingGaps ? "Buscando novas evidências..." : "Buscar evidências para preencher as lacunas"} {!fillingGaps && <ArrowRight size={18} />}</button>
    </aside>
  );
}
