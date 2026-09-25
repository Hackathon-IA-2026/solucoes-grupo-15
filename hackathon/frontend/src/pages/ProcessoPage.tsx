import { useEffect, useState } from "react";
import { ArrowRight, CalendarDays, FileText, GitBranch, Landmark, Network } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { fetchProcesso, ProcessoNotFoundError, type Processo } from "../api/processos";
import { DemoBanner } from "../components/DemoBanner";
import { RelationsPanel } from "../components/RelationsPanel";

/**
 * Página do processo SEI (TB1 Ticket 5, issue #21).
 *
 * Consome GET /v1/processos/{processoId}: lista as peças do processo
 * ordenadas por data (cada uma linkando para /documents/{family_id}),
 * mostra a cadeia `responde_a` entre peças do mesmo processo de forma
 * visível, e inclui o mesmo painel "Relações" (RelationsPanel) usado
 * na página de família — egocêntrico de um salto, centrado no
 * `processoId` desta vez.
 */

type ProcessoState =
  | { kind: "loading" }
  | { kind: "result"; processo: Processo }
  | { kind: "not-found" }
  | { kind: "error" };

export function ProcessoPage() {
  const { processoId } = useParams<{ processoId: string }>();
  const [state, setState] = useState<ProcessoState>({ kind: "loading" });

  useEffect(() => {
    if (!processoId) {
      return;
    }
    setState({ kind: "loading" });
    fetchProcesso(processoId)
      .then((processo) => setState({ kind: "result", processo }))
      .catch((error: unknown) => {
        if (error instanceof ProcessoNotFoundError) {
          setState({ kind: "not-found" });
        } else {
          setState({ kind: "error" });
        }
      });
  }, [processoId]);

  return (
    <div className="page detail-page">
      <DemoBanner />

      <section aria-label="página de processo">
        {state.kind === "loading" && <div className="loading-state"><span className="loading-spinner" aria-hidden="true" /> Carregando...</div>}
        {state.kind === "not-found" && <div className="empty-state"><h2>Processo não encontrado.</h2><Link to="/meus-processos">Voltar aos processos</Link></div>}
        {state.kind === "error" && <div className="empty-state error-state"><h2>Não foi possível carregar o processo.</h2><p>Tente novamente em alguns instantes.</p></div>}
        {state.kind === "result" && <ProcessoContent processo={state.processo} />}
      </section>
    </div>
  );
}

function ProcessoContent({ processo }: { processo: Processo }) {
  return (
    <div className="detail-layout process-layout">
      <div className="detail-primary">
      <header className="document-header process-header">
        <Link className="back-link" to="/meus-processos">Voltar aos processos</Link>
        <p className="eyebrow"><Landmark size={15} /> Processo administrativo</p>
        <h1>Processo {processo.processo_id}</h1>
        <p className="intro-copy">Linha documental e relações explícitas registradas para este processo.</p>
      </header>

      <section className="process-pieces" aria-label="peças do processo">
        <div className="section-heading"><div><p className="eyebrow"><FileText size={15} /> Linha do processo</p><h2>Peças</h2></div><span>{processo.pieces.length} documento{processo.pieces.length !== 1 ? "s" : ""}</span></div>
        {processo.pieces.length === 0 && <p>Nenhuma peça encontrada para este processo.</p>}
        <ol>
          {processo.pieces.map((piece) => (
            <li key={piece.family_id}>
              <span className="timeline-point" aria-hidden="true" />
              <div>
                <p><CalendarDays size={14} /> {piece.version_date}</p>
                <Link to={`/documents/${encodeURIComponent(piece.family_id)}`}>
                  {piece.document_type} — {piece.document_id} <ArrowRight size={15} aria-hidden="true" />
                </Link>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="response-chain" aria-label="cadeia de respostas">
        <div className="section-heading"><div><p className="eyebrow"><GitBranch size={15} /> Relação processual</p><h2>Cadeia de respostas</h2></div></div>
        {processo.responde_a.length === 0 && (
          <p>Nenhuma resposta explícita registrada entre as peças deste processo.</p>
        )}
        <ul>
          {processo.responde_a.map((edge) => (
            <li key={`${edge.source_family_id}-${edge.target_family_id}`}>
              <span className="sr-only">{edge.source_family_id} responde a {edge.target_family_id}</span>
              <span>{edge.source_family_id}</span><ArrowRight size={15} aria-hidden="true" /><span>responde a</span><ArrowRight size={15} aria-hidden="true" /><span>{edge.target_family_id}</span>
            </li>
          ))}
        </ul>
      </section>
      </div>

      <aside className="detail-sidebar">
        <div className="sidebar-title"><Network size={17} /><span>Contexto conectado</span></div>
        <RelationsPanel nodeId={processo.processo_id} />
      </aside>
    </div>
  );
}

export default ProcessoPage;
