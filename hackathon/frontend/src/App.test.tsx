import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
    vi.stubGlobal("fetch", buildFetchMock());
  });

  afterEach(() => vi.unstubAllGlobals());

  it("conduz do login para a escolha de persona e para o shell do produto", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("heading", { name: /como você quer usar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /advogados/i })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: /continuar/i })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /advogados/i }));
    fireEvent.click(screen.getByRole("button", { name: /continuar/i }));

    await waitFor(() => expect(window.location.pathname).toBe("/explorar"));
    expect(screen.getByRole("navigation", { name: /navegação principal do produto/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /meus processos/i })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /notificações, 1 não lidas/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /ainda não há uma pesquisa/i })).toBeInTheDocument();
  });

  it("mantém sair dentro do menu da conta e encerra a sessão", async () => {
    window.localStorage.setItem("capiwatt-lens:mock-session", JSON.stringify({
      user: { id: "carolina", name: "Carolina", firstName: "Carol", initials: "CA", email: "carolina@capiwatt.demo" },
      activePersona: "advocacia",
    }));
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /Carol/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /sair/i }));

    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(screen.getByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  it("abre notificações no sino sem sair da página", async () => {
    window.localStorage.setItem("capiwatt-lens:mock-session", JSON.stringify({
      user: { id: "carolina", name: "Carolina", firstName: "Carol", initials: "CA", email: "carolina@capiwatt.demo" },
      activePersona: "advocacia",
    }));
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /notificações, 1 não lidas/i }));
    expect(screen.getByRole("region", { name: /notificações não lidas/i })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/explorar");
    fireEvent.click(screen.getByRole("button", { name: /auto-0007/i }));
    await waitFor(() => expect(window.location.pathname).toContain("/documents/fam-auto-0007"));
    expect(screen.getByRole("button", { name: /notificações, 0 não lidas/i })).toBeInTheDocument();
  });

  it("confirma o reset da demonstração pelo menu da conta", async () => {
    window.localStorage.setItem("capiwatt-lens:mock-session", JSON.stringify({
      user: { id: "carolina", name: "Carolina", firstName: "Carol", initials: "CA", email: "carolina@capiwatt.demo" },
      activePersona: "advocacia",
    }));
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /Carol/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /resetar demonstração/i }));
    expect(screen.getByRole("dialog", { name: /resetar demonstração/i })).toHaveTextContent(/corpus documental.*preservado/i);
    fireEvent.click(screen.getByRole("button", { name: /confirmar reset/i }));

    await waitFor(() => expect(screen.queryByRole("dialog", { name: /resetar demonstração/i })).not.toBeInTheDocument());
    expect(fetch).toHaveBeenCalledWith("/v1/demo/reset", { method: "POST" });
    expect(window.location.pathname).toBe("/explorar");
  });
});

function buildFetchMock() {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/v1/health") return jsonResponse({ backend: "ok", ai: "ok" });
    if (url === "/v1/ingestions" && init?.method === "POST") return jsonResponse({ ingestion_job_id: "job-1", families_count: 4, versions_count: 5, relations_count: 5 });
    if (url.endsWith("/notification-scope")) return jsonResponse({ scope: "estrita" });
    if (url.endsWith("/email-digests")) return jsonResponse([{ email_id: "carolina:job-1", user_id: "carolina", ingestion_job_id: "job-1", notification_ids: [5], rendered_body: "Você tem 1 novo documento", created_at: "2024-05-02T12:00:00Z" }]);
    if (url.endsWith("/notifications")) return jsonResponse([{ id: 5, user_id: "carolina", document_version_id: "docver-auto-0007-v2", family_id: "fam-auto-0007", document_type: "auto_de_infracao", document_id: "auto-0007", scope_effective: "estrita", reasons: [{ type: "novo_documento" }], ingestion_job_id: "job-1", created_at: "2024-05-02T12:00:00Z", opened: false }]);
    if (url.endsWith("/opened")) return jsonResponse({ notification_id: 5, opened: true });
    if (url === "/v1/demo/reset") return jsonResponse({ deleted: { notifications: 1 } });
    return jsonResponse({}, 404);
  });
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
