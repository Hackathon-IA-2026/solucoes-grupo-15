/**
 * Cliente do frontend para o feedback 👍/👎 sobre um card de resultado
 * de busca (TB1 Ticket 7, issue #23).
 *
 * Chama so POST /v1/feedback no backend. Liga o voto ao ``request_id``
 * do envelope de POST /v1/search (ticket 3, issue #19) que produziu o
 * card e ao ``family_id`` avaliado - nenhum campo de
 * justificativa/comentario existe aqui, por decisao explicita da
 * issue.
 */

export type Vote = "up" | "down";

export type Feedback = {
  id: number;
  request_id: string;
  family_id: string;
  vote: Vote;
  created_at: string;
};

export async function submitFeedback(
  requestId: string,
  familyId: string,
  vote: Vote,
): Promise<Feedback> {
  const response = await fetch("/v1/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_id: requestId, family_id: familyId, vote }),
  });

  if (!response.ok) {
    throw new Error(`Envio de feedback falhou com status ${response.status}`);
  }

  return (await response.json()) as Feedback;
}
