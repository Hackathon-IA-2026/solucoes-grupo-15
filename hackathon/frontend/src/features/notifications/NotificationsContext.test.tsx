import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionProvider } from "../auth/SessionContext";
import { DemoDataProvider } from "../demo/DemoDataContext";
import { NotificationsProvider, useNotifications } from "./NotificationsContext";

const notification = {
  id: 5,
  user_id: "carolina",
  document_version_id: "docver-auto-0007-v2",
  family_id: "fam-auto-0007",
  document_type: "auto_de_infracao",
  document_id: "auto-0007",
  scope_effective: "estrita",
  reasons: [{ type: "novo_documento" }],
  ingestion_job_id: "job-1",
  created_at: "2024-05-02T12:00:00Z",
  opened: false,
};

describe("NotificationsContext", () => {
  beforeEach(() => {
    window.localStorage.setItem("capiwatt-lens:mock-session", JSON.stringify({
      user: { id: "carolina", name: "Carolina", firstName: "Carol", initials: "CA", email: "carolina@capiwatt.demo" },
      activePersona: "advocacia",
    }));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("exige escolha explícita, reingere e carrega notificações", async () => {
    const fetchMock = buildFetchMock(null);
    vi.stubGlobal("fetch", fetchMock);
    renderProbe();

    expect(await screen.findByText("scope-required")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /escolher estrita/i }));

    expect(await screen.findByText("1 não lidas")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/users/carolina/notification-scope",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(fetchMock).toHaveBeenCalledWith("/v1/ingestions", { method: "POST" });
  });

  it("registra abertura e atualiza o total compartilhado", async () => {
    const fetchMock = buildFetchMock("estrita");
    vi.stubGlobal("fetch", fetchMock);
    renderProbe();

    expect(await screen.findByText("1 não lidas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /abrir notificação/i }));

    await waitFor(() => expect(screen.getByText("0 não lidas")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/notifications/5/opened",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("reseta as interações e volta a exigir a escolha de escopo", async () => {
    const fetchMock = buildFetchMock("estrita");
    vi.stubGlobal("fetch", fetchMock);
    renderProbe();

    expect(await screen.findByText("1 não lidas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /resetar estado/i }));

    expect(await screen.findByText("scope-required")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/v1/demo/reset", { method: "POST" });
  });
});

function renderProbe() {
  render(
    <SessionProvider>
      <DemoDataProvider>
        <NotificationsProvider><Probe /></NotificationsProvider>
      </DemoDataProvider>
    </SessionProvider>,
  );
}

function Probe() {
  const state = useNotifications();
  if (state.kind === "scope-required") return <><span>scope-required</span><button type="button" onClick={() => void state.chooseScope("estrita")}>Escolher estrita</button></>;
  if (state.kind !== "ready") return <span>{state.kind}</span>;
  const unread = state.notifications.filter((item) => !item.opened).length;
  return <><span>{unread} não lidas</span><button type="button" onClick={() => void state.openNotification(5)}>Abrir notificação</button><button type="button" onClick={() => void state.resetDemo()}>Resetar estado</button></>;
}

function buildFetchMock(initialScope: "estrita" | null) {
  let scope = initialScope;
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/v1/health") return jsonResponse({ backend: "ok", ai: "ok" });
    if (url === "/v1/ingestions") return jsonResponse({ ingestion_job_id: "job-1", families_count: 4, versions_count: 5, relations_count: 5 });
    if (url.endsWith("/notification-scope")) {
      if (init?.method === "PUT") scope = "estrita";
      return jsonResponse({ scope });
    }
    if (url.endsWith("/email-digests")) return jsonResponse([]);
    if (url.endsWith("/notifications")) return jsonResponse([notification]);
    if (url.endsWith("/opened")) return jsonResponse({ notification_id: 5, opened: true });
    if (url === "/v1/demo/reset") return jsonResponse({ deleted: { notifications: 1 } });
    return jsonResponse({}, 404);
  });
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
