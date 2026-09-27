import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch, setRequestHeadersProvider } from "./client";
import { resetDemoState } from "./demo";
import { fetchDocument } from "./documents";
import { submitFeedback } from "./feedback";
import { fetchBackendHealth } from "./health";
import { runDemoIngestion } from "./ingestions";
import {
  chooseNotificationScope,
  fetchEmailDigests,
  fetchNotificationScope,
  fetchNotifications,
  markNotificationOpened,
} from "./notifications";
import { fetchProcesso, fetchProcessos } from "./processos";
import { fetchGraph } from "./relations";
import { searchDocuments } from "./search";

describe("apiFetch (ponto único do cliente /v1)", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn(async () => new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    setRequestHeadersProvider(null);
    vi.unstubAllGlobals();
  });

  it("sem provedor de headers, repassa caminho relativo e init sem alteração (modo demo)", async () => {
    await apiFetch("/v1/health");
    await apiFetch("/v1/demo/reset", { method: "POST" });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/v1/health");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/v1/demo/reset", { method: "POST" });
  });

  it("acrescenta os headers do provedor em cada requisição, preservando os headers da chamada", async () => {
    let token = "token-1";
    setRequestHeadersProvider(async () => ({ Authorization: `Bearer ${token}` }));

    await apiFetch("/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    token = "token-2";
    await apiFetch("/v1/health");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer token-1" },
      body: "{}",
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/v1/health", {
      headers: { Authorization: "Bearer token-2" },
    });
  });

  it("todas as funções de API passam pelo ponto único, com caminhos relativos e ids codificados", async () => {
    setRequestHeadersProvider(() => ({ Authorization: "Bearer t" }));
    fetchMock.mockImplementation(async () => new Response(JSON.stringify({ scope: null }), { status: 200 }));

    await fetchBackendHealth();
    await searchDocuments("microgeração");
    await fetchDocument("fam/1", "v 2");
    await fetchGraph("48500.001234/2024-11");
    await fetchProcessos();
    await fetchProcesso("48500.001234/2024-11");
    await submitFeedback("r1", "fam-1", "v1", 0, "up");
    await fetchNotificationScope("carol ina");
    await chooseNotificationScope("carol ina", "ampla");
    await fetchNotifications("carol ina");
    await fetchEmailDigests("carol ina");
    await markNotificationOpened(5);
    await runDemoIngestion();
    await resetDemoState();

    const calls = fetchMock.mock.calls as [string, RequestInit][];
    expect(calls.map(([path]) => path)).toEqual([
      "/v1/health",
      "/v1/search",
      "/v1/documents/fam%2F1?version=v%202",
      "/v1/documents/48500.001234%2F2024-11/graph",
      "/v1/processos",
      "/v1/processos/48500.001234%2F2024-11",
      "/v1/feedback",
      "/v1/users/carol%20ina/notification-scope",
      "/v1/users/carol%20ina/notification-scope",
      "/v1/users/carol%20ina/notifications",
      "/v1/users/carol%20ina/email-digests",
      "/v1/notifications/5/opened",
      "/v1/ingestions",
      "/v1/demo/reset",
    ]);
    for (const [path, init] of calls) {
      expect(init?.headers, path).toMatchObject({ Authorization: "Bearer t" });
    }
  });
});
