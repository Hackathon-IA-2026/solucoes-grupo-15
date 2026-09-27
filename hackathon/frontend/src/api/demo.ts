import { apiFetch } from "./client";

export type DemoResetReport = {
  deleted: Record<string, number>;
};

export async function resetDemoState(): Promise<DemoResetReport> {
  const response = await apiFetch("/v1/demo/reset", { method: "POST" });
  if (!response.ok) {
    throw new Error(`Reset da demonstração falhou com status ${response.status}`);
  }
  return (await response.json()) as DemoResetReport;
}
