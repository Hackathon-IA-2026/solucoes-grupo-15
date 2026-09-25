import { fetchBackendHealth } from "./health";

export type DemoIngestion = {
  ingestion_job_id: string;
  families_count: number;
  versions_count: number;
  relations_count: number;
};

export async function prepareDemoData(): Promise<DemoIngestion> {
  const health = await fetchBackendHealth();
  if (health.backend !== "ok" || health.ai !== "ok") {
    throw new Error("Backend ou serviço de IA indisponível");
  }

  return runDemoIngestion();
}

export async function runDemoIngestion(): Promise<DemoIngestion> {
  const response = await fetch("/v1/ingestions", { method: "POST" });
  if (!response.ok) {
    throw new Error(`Preparação demo falhou com status ${response.status}`);
  }

  return (await response.json()) as DemoIngestion;
}
