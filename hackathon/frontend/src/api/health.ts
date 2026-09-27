/**
 * Cliente do frontend para o health check cruzado do backend.
 *
 * Chama so GET /v1/health no backend (nunca o ai nem o indice vetorial
 * diretamente), conforme a fronteira de modulos decidida na arquitetura.
 */

import { apiFetch } from "./client";

export type BackendHealth = {
  backend: string;
  ai: string;
};

export async function fetchBackendHealth(): Promise<BackendHealth> {
  const response = await apiFetch("/v1/health");

  if (!response.ok) {
    throw new Error(`Health check falhou com status ${response.status}`);
  }

  return (await response.json()) as BackendHealth;
}
