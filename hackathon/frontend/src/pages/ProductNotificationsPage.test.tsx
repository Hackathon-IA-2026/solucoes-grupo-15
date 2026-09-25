import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionProvider } from "../features/auth/SessionContext";
import { DemoDataProvider } from "../features/demo/DemoDataContext";
import { NotificationsProvider } from "../features/notifications/NotificationsContext";
import { ProductNotificationsPage } from "./ProductNotificationsPage";

describe("ProductNotificationsPage integrada", () => {
  beforeEach(() => {
    window.localStorage.setItem("capiwatt-lens:mock-session", JSON.stringify({
      user: { id: "carolina", name: "Carolina", firstName: "Carol", initials: "CA", email: "carolina@capiwatt.demo" },
      activePersona: "advocacia",
    }));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("mostra motivos e digest e abre o documento", async () => {
    const fetchMock = buildFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    renderPage();

    expect(await screen.findByText("auto-0007")).toBeInTheDocument();
    expect(screen.getByText("Documento novo indexado")).toBeInTheDocument();
    expect(screen.getByText(/você tem 1 novo documento/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /não lidas \(1\)/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /abrir e marcar como lida/i }));

    expect(await screen.findByText(/documento aberto/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/notifications/5/opened",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("oferece nova tentativa quando a lista falha", async () => {
    vi.stubGlobal("fetch", buildFetchMock(true));
    renderPage();

    expect(await screen.findByText(/não foi possível carregar as notificações/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tentar novamente/i })).toBeInTheDocument();
  });
});

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/notificacoes"]}>
      <SessionProvider>
        <DemoDataProvider>
          <NotificationsProvider>
            <Routes>
              <Route path="/notificacoes" element={<ProductNotificationsPage />} />
              <Route path="/documents/:familyId" element={<p>Documento aberto</p>} />
            </Routes>
          </NotificationsProvider>
        </DemoDataProvider>
      </SessionProvider>
    </MemoryRouter>,
  );
}

function buildFetchMock(failNotifications = false) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/v1/health") return jsonResponse({ backend: "ok", ai: "ok" });
    if (url === "/v1/ingestions") return jsonResponse({ ingestion_job_id: "job-1", families_count: 4, versions_count: 5, relations_count: 5 });
    if (url.endsWith("/notification-scope")) return jsonResponse({ scope: "estrita" });
    if (url.endsWith("/email-digests")) return jsonResponse([{ email_id: "carolina:job-1", user_id: "carolina", ingestion_job_id: "job-1", notification_ids: [5], rendered_body: "Você tem 1 novo documento", created_at: "2024-05-02T12:00:00Z" }]);
    if (url.endsWith("/notifications")) return failNotifications ? jsonResponse({}, 500) : jsonResponse([{ id: 5, user_id: "carolina", document_version_id: "docver-auto-0007-v2", family_id: "fam-auto-0007", document_type: "auto_de_infracao", document_id: "auto-0007", scope_effective: "estrita", reasons: [{ type: "novo_documento" }], ingestion_job_id: "job-1", created_at: "2024-05-02T12:00:00Z", opened: false }]);
    if (url.endsWith("/opened") && init?.method === "POST") return jsonResponse({ notification_id: 5, opened: true });
    return jsonResponse({}, 404);
  });
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
