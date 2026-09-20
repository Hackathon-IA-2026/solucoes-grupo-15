import { useState } from "react";

import { submitFeedback, type Vote } from "../api/feedback";

/**
 * Botões 👍/👎 de um card de resultado de busca (TB1 Ticket 7, issue #23).
 *
 * Chama POST /v1/feedback com ``requestId`` (do envelope de busca,
 * ticket 3) e ``familyId`` do card. Depois de um voto bem-sucedido,
 * mostra uma mensagem simples e desabilita os dois botões - so para
 * não votar duas vezes por engano nesse card; não é exigido pela
 * issue, mas é razoável para uma UI operacional. Sem edição de voto,
 * sem comentário (fora de escopo). Falha de rede mostra uma mensagem
 * de erro simples, sem travar o restante da página - os botões
 * continuam habilitados para tentar de novo.
 */

type ButtonsState =
  | { kind: "idle" }
  | { kind: "submitting"; vote: Vote }
  | { kind: "done"; vote: Vote }
  | { kind: "error" };

export function FeedbackButtons({
  requestId,
  familyId,
}: {
  requestId: string;
  familyId: string;
}) {
  const [state, setState] = useState<ButtonsState>({ kind: "idle" });

  function vote(vote: Vote) {
    setState({ kind: "submitting", vote });
    submitFeedback(requestId, familyId, vote)
      .then(() => setState({ kind: "done", vote }))
      .catch(() => setState({ kind: "error" }));
  }

  const disabled = state.kind === "submitting" || state.kind === "done";

  return (
    <div aria-label="feedback sobre este resultado">
      <button
        type="button"
        aria-label="votar positivamente"
        disabled={disabled}
        onClick={() => vote("up")}
      >
        👍
      </button>
      <button
        type="button"
        aria-label="votar negativamente"
        disabled={disabled}
        onClick={() => vote("down")}
      >
        👎
      </button>
      {state.kind === "done" && <p>Obrigado pelo feedback</p>}
      {state.kind === "error" && <p>Não foi possível registrar o feedback.</p>}
    </div>
  );
}

export default FeedbackButtons;
