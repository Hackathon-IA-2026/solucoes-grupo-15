import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../../App";

const session = {
  user: {
    id: "carolina",
    name: "Carolina",
    firstName: "Carol",
    initials: "CA",
    email: "carolina@capiwatt.demo",
  },
  activePersona: "advocacia",
};

describe("preparação dos dados demo", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("capiwatt-lens:mock-session", JSON.stringify(session));
    window.history.pushState({}, "", "/explorar");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("prepara o corpus uma vez e mantém o estado pronto ao navegar", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/v1/health") return jsonResponse({ backend: "ok", ai: "ok" });
      if (url === "/v1/ingestions") return jsonResponse({ ingestion_job_id: "job-1", families_count: 4, versions_count: 5, relations_count: 6 });
      if (url.endsWith("/notification-scope")) return jsonResponse({ scope: null });
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Dados demo prontos")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/v1/health");
    expect(fetchMock).toHaveBeenCalledWith("/v1/ingestions", { method: "POST" });
    const callsBeforeNavigation = fetchMock.mock.calls.length;

    fireEvent.click(screen.getByRole("link", { name: /famílias/i }));
    await waitFor(() => expect(window.location.pathname).toBe("/familias"));
    expect(fetchMock).toHaveBeenCalledTimes(callsBeforeNavigation);
  });

  it("mostra indisponibilidade e permite tentar preparar novamente", async () => {
    let healthCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/v1/health") {
        healthCalls += 1;
        return jsonResponse({ backend: "ok", ai: healthCalls === 1 ? "unreachable" : "ok" });
      }
      if (url === "/v1/ingestions") return jsonResponse({ ingestion_job_id: "job-2", families_count: 4, versions_count: 5, relations_count: 6 });
      if (url.endsWith("/notification-scope")) return jsonResponse({ scope: null });
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const retry = await screen.findByRole("button", { name: /modo demo indisponível/i });
    fireEvent.click(retry);

    expect(await screen.findByText("Dados demo prontos")).toBeInTheDocument();
    expect(healthCalls).toBe(2);
    expect(fetchMock).toHaveBeenCalledWith("/v1/ingestions", { method: "POST" });
  });
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
