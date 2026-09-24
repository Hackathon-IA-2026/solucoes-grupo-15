import { AlertTriangle, CheckCircle2, Download, FileCheck2, FileText, History, Scale, Share2 } from "lucide-react";
import { useEffect, useState, type CSSProperties } from "react";

import { PageHero } from "../components/layout/PageHero";
import { appRepository } from "../services/appRepository";
import type { OpinionData } from "../types/product";

export function OpinionPage() {
  const [opinion, setOpinion] = useState<OpinionData | null>(null);
  const [tab, setTab] = useState("Parecer Conclusivo");
  const [shared, setShared] = useState(false);
  useEffect(() => { appRepository.getOpinion().then(setOpinion); }, []);

  function exportOpinion() {
    if (!opinion) return;
    const text = `${opinion.title}\nProcesso: ${opinion.processNumber}\n\n${opinion.verdict}\n${opinion.verdictSummary}\n\nEntendimento sugerido\n${opinion.suggestedUnderstanding}`;
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `parecer-${opinion.code}.txt`; anchor.click(); URL.revokeObjectURL(url);
  }

  if (!opinion) return <div className="product-page"><div className="skeleton opinion-skeleton" /></div>;
  return (
    <div className="product-page"><PageHero icon={FileCheck2} title={opinion.title} description={`Processo SEI ${opinion.processNumber} · ${opinion.family}`} />
      <nav className="content-tabs" aria-label="Seções do parecer">{["Parecer Conclusivo","Contexto e Histórico","Evidências (10)","Discussões Relacionadas","Linha do Tempo"].map((item) => <button type="button" className={tab === item ? "active" : ""} key={item} onClick={() => setTab(item)}>{item}</button>)}</nav>
      <div className="opinion-layout"><section className="opinion-main">{tab === "Parecer Conclusivo" ? <><article className="verdict-card"><CheckCircle2 size={38} /><div><small>Entendimento sugerido</small><h2>{opinion.verdict}</h2></div><p>{opinion.verdictSummary}</p></article><OpinionSection icon={FileText} title="Situação" text={opinion.situation} /><OpinionSection icon={Scale} title="Entendimento sugerido" text={opinion.suggestedUnderstanding} /><article className="opinion-section attention"><AlertTriangle /><div><h2>Pontos de atenção</h2><ul>{opinion.attentionPoints.map((point) => <li key={point}>{point}</li>)}</ul></div></article><section><h2 className="section-title">Valores e números citados</h2><div className="figure-grid">{opinion.figures.map((figure) => <article className={`figure-card ${figure.tone}`} key={figure.label}><strong>{figure.value}</strong><span>{figure.label}</span></article>)}</div></section></> : <article className="opinion-placeholder"><History size={34} /><h2>{tab}</h2><p>Esta visão organiza o mesmo parecer por {tab.toLowerCase()}, mantendo a rastreabilidade com as evidências mockadas do caso MMGD.</p></article>}</section><aside className="summary-sidebar opinion-sidebar"><h2>Informações do parecer</h2><dl className="detail-list"><div><dt>Código</dt><dd>{opinion.code}</dd></div><div><dt>Data de emissão</dt><dd>{opinion.issuedAt}</dd></div><div><dt>Status</dt><dd>{opinion.status}</dd></div><div><dt>Responsável</dt><dd>CapiWatt Lens (Carol)</dd></div></dl><h3>Confiança e cobertura</h3><div className="opinion-rings"><MetricRing label="Confiança" value={opinion.confidence} /><MetricRing label="Cobertura" value={opinion.coverage} /></div><h3>Ações</h3><button className="yellow-button opinion-action" type="button" onClick={exportOpinion}><Download size={18} /> Exportar parecer</button><button className="outline-action" type="button" onClick={() => setShared(true)}><Share2 size={17} /> {shared ? "Link copiado" : "Compartilhar"}</button></aside></div>
    </div>
  );
}

function OpinionSection({ icon: Icon, title, text }: { icon: typeof FileText; title: string; text: string }) { return <article className="opinion-section"><Icon /><div><h2>{title}</h2><p>{text}</p></div></article>; }
function MetricRing({ label, value }: { label: string; value: number }) { return <div><span className="metric-ring" style={{ "--metric": `${value*3.6}deg` } as CSSProperties}><strong>{value}%</strong></span><b>{label}</b></div>; }
