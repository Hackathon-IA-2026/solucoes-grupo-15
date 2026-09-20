/**
 * Cliente do frontend para a pagina de processo SEI (TB1 Ticket 5, issue #21).
 *
 * Chama so GET /v1/processos/{processoId} no backend. Ver
 * hackathon/backend/app/routes/relations.py para a forma exata do
 * envelope. ``processoId`` sempre passa por ``encodeURIComponent`` -
 * mesma razao de api/relations.ts (o numero SEI contem "/").
 */

import type { RelationEvidence } from "./relations";

export type ProcessoPiece = {
  family_id: string;
  document_type: string;
  document_id: string;
  version_date: string;
};

export type RespondeAEdge = {
  source_family_id: string;
  target_family_id: string;
  evidence: RelationEvidence | null;
};

export type Processo = {
  processo_id: string;
  pieces: ProcessoPiece[];
  responde_a: RespondeAEdge[];
};

/**
 * Sinaliza especificamente o 404 de "processo nao encontrado".
 */
export class ProcessoNotFoundError extends Error {}

export async function fetchProcesso(processoId: string): Promise<Processo> {
  const response = await fetch(`/v1/processos/${encodeURIComponent(processoId)}`);

  if (response.status === 404) {
    throw new ProcessoNotFoundError("Processo não encontrado");
  }
  if (!response.ok) {
    throw new Error(`Consulta de processo falhou com status ${response.status}`);
  }

  return (await response.json()) as Processo;
}
