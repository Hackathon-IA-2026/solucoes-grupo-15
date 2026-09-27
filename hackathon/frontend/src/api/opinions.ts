import type { OpinionData } from '../types/product';

export async function fetchOpinion(processoNumero: string): Promise<OpinionData> {
  const response = await fetch(`/v1/processos/${encodeURIComponent(processoNumero)}/resultado`);
  if (!response.ok) throw new Error(`opinion failed ${response.status}`);
  return (await response.json()) as OpinionData;
}
