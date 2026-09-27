import { afterEach, expect, it, vi } from "vitest";

import { ApiAppRepository } from "./appRepository";

afterEach(() => vi.unstubAllGlobals());

it("reads processes, families, opinion and notifications through backend HTTP", async () => {
  window.localStorage.clear();
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const path = String(input);
    const responses: Record<string, unknown> = {
      "/v1/processos": [{ processo_id: "48500.004024/2017-80", latest_movement_at: "2020-01-01", latest_document_type: "voto", latest_document_id: "Voto Enel", pieces_count: 3, document_types: ["voto"] }],
      "/v1/families": [{ family_id: "case1-enel-voto", document_id: "Voto Enel", document_type: "voto", processo_numero: "48500.004024/2017-80", versions_count: 1, latest_version_date: "2020-01-01" }],
      "/v1/opinion": { title: "Parecer demonstrativo", processNumber: "48500.004024/2017-80", verdict: "Trecho real" },
      "/v1/users/carolina/notifications": [{ id: 7, document_id: "Voto Enel", document_version_id: "case1-enel-voto-2020", family_id: "case1-enel-voto", document_type: "voto", reasons: [{ type: "novo_documento" }], created_at: "2026-09-27T10:00:00Z", opened: false }],
    };
    return Promise.resolve(new Response(JSON.stringify(responses[path]), { status: path in responses ? 200 : 404 }));
  });
  vi.stubGlobal("fetch", fetchMock);
  const repository = new ApiAppRepository();

  expect((await repository.getProcessDashboard()).processes[0].processo_id).toBe("48500.004024/2017-80");
  expect((await repository.getFamilies())[0].id).toBe("case1-enel-voto");
  expect((await repository.getOpinion()).verdict).toBe("Trecho real");
  expect((await repository.getNotifications())[0].title).toBe("Voto Enel");
  expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
    "/v1/processos", "/v1/families", "/v1/opinion", "/v1/users/carolina/notifications",
  ]);
});
