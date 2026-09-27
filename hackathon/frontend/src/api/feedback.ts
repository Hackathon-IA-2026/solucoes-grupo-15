/**
 * Cliente do frontend para o feedback 👍/👎 sobre um resultado de busca
 * (TB1 Ticket 7, issue #23; chave de chunk issues #82/#94).
 *
 * Chama so POST /v1/feedback no backend. Desde a issue #82 o voto
 * identifica o chunk exato avaliado: ``document_version`` +
 * ``chunk_index`` (indice real do chunk no documento, devolvido em cada
 * resultado de POST /v1/search desde a issue #96), alem do
 * ``request_id`` do envelope de busca que produziu o resultado. O
 * ``family_id`` nao e enviado (o backend o aceita como opcional so por
 * compatibilidade legada). Nenhum campo de justificativa/comentario
 * existe aqui, por decisao explicita da issue #23.
 */

import { apiFetch } from "./client";

export type Vote = "up" | "down";

/** O chunk avaliado, na busca que o produziu. */
export type FeedbackTarget = {
  requestId: string;
  documentVersion: string;
  chunkIndex: number;
};

export type Feedback = {
  id: number;
  request_id: string;
  document_version: string | null;
  chunk_index: number | null;
  family_id: string | null;
  vote: Vote;
  created_at: string;
};

export async function submitFeedback(target: FeedbackTarget, vote: Vote): Promise<Feedback> {
  const response = await apiFetch("/v1/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request_id: target.requestId,
      document_version: target.documentVersion,
      chunk_index: target.chunkIndex,
      vote,
    }),
  });

  if (!response.ok) {
    throw new Error(`Envio de feedback falhou com status ${response.status}`);
  }

  return (await response.json()) as Feedback;
}
