import { apiFetch } from "./client";
import type { OpinionData } from "../types/product";

export async function fetchOpinion(): Promise<OpinionData> {
  const response = await apiFetch("/v1/opinion");
  if (!response.ok) throw new Error(`Consulta de parecer falhou com status ${response.status}`);
  return (await response.json()) as OpinionData;
}
