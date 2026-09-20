import { useEffect, useState } from "react";
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
    <div>
      <DemoBanner />

      <section aria-label="página de processo">
        {state.kind === "loading" && <p>Carregando...</p>}
        {state.kind === "not-found" && <p>Processo não encontrado.</p>}
        {state.kind === "error" && <p>Não foi possível carregar o processo.</p>}
        {state.kind === "result" && <ProcessoContent processo={state.processo} />}
      </section>
    </div>
  );
}

function ProcessoContent({ processo }: { processo: Processo }) {
  return (
    <div>
      <header>
        <h2>Processo {processo.processo_id}</h2>
      </header>

      <section aria-label="peças do processo">
        <h3>Peças</h3>
        {processo.pieces.length === 0 && <p>Nenhuma peça encontrada para este processo.</p>}
        <ol>
          {processo.pieces.map((piece) => (
            <li key={piece.family_id}>
              <Link to={`/documents/${encodeURIComponent(piece.family_id)}`}>
                {piece.document_type} — {piece.document_id}
              </Link>
              <span> ({piece.version_date})</span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-label="cadeia de respostas">
        <h3>Cadeia de respostas</h3>
        {processo.responde_a.length === 0 && (
          <p>Nenhuma resposta explícita registrada entre as peças deste processo.</p>
        )}
        <ul>
          {processo.responde_a.map((edge) => (
            <li key={`${edge.source_family_id}-${edge.target_family_id}`}>
              {edge.source_family_id} responde a {edge.target_family_id}
            </li>
          ))}
        </ul>
      </section>

      <RelationsPanel nodeId={processo.processo_id} />
    </div>
  );
}

export default ProcessoPage;
