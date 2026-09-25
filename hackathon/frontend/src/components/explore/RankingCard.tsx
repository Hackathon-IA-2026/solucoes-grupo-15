import { Building2, CalendarDays, ChevronDown, ChevronUp, FileText, FolderOpen } from "lucide-react";
import { useState } from "react";

import { FeedbackButtons } from "../FeedbackButtons";
import type { RankedPrecedent } from "../../types/product";

export function RankingCard({ result, onOpenDocuments }: { result: RankedPrecedent; onOpenDocuments: (result: RankedPrecedent) => void }) {
  const [expanded, setExpanded] = useState(result.rank === 1);
  return (
    <article className="ranking-card">
      <div className={`rank-number rank-${result.rank}`}>{result.rank}</div>
      <div className="ranking-main">
        <div className="ranking-title-row">
          <div><span className="result-kind">Família documental</span><h3>{result.processNumber}</h3><small className="document-identity">{result.documents[0]?.label} · {result.familyId}</small></div>
          <div className="ranking-badges"><span className="status-chip green">{result.relevance}</span><span className={`status-chip ${result.stance === "Precedente contrário" ? "red" : result.stance === "Em andamento" ? "orange" : "blue"}`}>{result.stance}</span><span className="adherence"><strong>{result.adherence}%</strong><small>Aderência</small></span></div>
        </div>
        <p className="ranking-summary">{result.summary}</p>
        <div className="ranking-meta"><span><Building2 size={14} /> {result.agency}</span><span><CalendarDays size={14} /> {result.period}</span>{result.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>
        <div className="ranking-actions">
          <button type="button" onClick={() => setExpanded((open) => !open)}>{expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />} {result.rank === 1 ? "Por que está no topo?" : "Por que está ranqueado?"}</button>
          <button type="button" onClick={() => onOpenDocuments(result)}><FileText size={16} /> {result.documents.length} documento{result.documents.length === 1 ? "-chave" : "s-chave"} <FolderOpen size={16} /></button>
          {result.requestId && result.familyId && <FeedbackButtons requestId={result.requestId} familyId={result.familyId} />}
        </div>
        {expanded && <div className="ranking-explanation"><strong>Motivos do ranking</strong><ul>{result.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul><p><b>Agente:</b> {result.distributor} · <b>Tema:</b> {result.theme}</p></div>}
      </div>
    </article>
  );
}
