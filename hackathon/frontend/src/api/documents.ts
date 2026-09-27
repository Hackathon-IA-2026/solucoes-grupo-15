/**
 * Cliente do frontend para a leitura de documento por familia (TB1
 * Ticket 4, issue #20).
 *
 * Chama so GET /v1/documents/{familyId} no backend (nunca o ai nem o
 * indice vetorial diretamente). Os tipos abaixo espelham o envelope de
 * resposta documentado em hackathon/backend/app/routes/documents.py.
 */

import { apiFetch } from "./client";

export type VersionSummary = {
  document_version: string;
  version_date: string;
  version_date_source: string;
};

export type SelectedVersion = VersionSummary & {
  text: string;
};

export type DocumentDetail = {
  family_id: string;
  document_id: string;
  document_type: string;
  processo_numero: string | null;
  versions: VersionSummary[];
  selected_version: SelectedVersion;
  source_pdf_url: string | null;
};

export type FamilySummary = {
  family_id: string;
  document_id: string;
  document_type: string;
  processo_numero: string | null;
  versions_count: number;
  latest_version_date: string;
};

export async function fetchFamilies(): Promise<FamilySummary[]> {
  const response = await apiFetch("/v1/families");
  if (!response.ok) throw new Error(`Consulta de famílias falhou com status ${response.status}`);
  return (await response.json()) as FamilySummary[];
}

/**
 * Sinaliza especificamente o 404 de "familia nao encontrada", para a
 * pagina distinguir esse caso (mensagem clara) de uma falha de rede
 * generica.
 */
export class DocumentNotFoundError extends Error {}

export async function fetchDocument(
  familyId: string,
  version?: string,
): Promise<DocumentDetail> {
  const query = version ? `?version=${encodeURIComponent(version)}` : "";
  const response = await apiFetch(`/v1/documents/${encodeURIComponent(familyId)}${query}`);

  if (response.status === 404) {
    throw new DocumentNotFoundError("Família não encontrada");
  }
  if (!response.ok) {
    throw new Error(`Consulta de documento falhou com status ${response.status}`);
  }

  return (await response.json()) as DocumentDetail;
}
