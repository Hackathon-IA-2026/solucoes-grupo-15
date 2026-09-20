import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NotificationsPage } from "./NotificationsPage";

const SAMPLE_NOTIFICATION = {
  id: 5,
  user_id: "carolina",
  document_version_id: "docver-auto-0007-v2",
  family_id: "fam-auto-0007",
  document_type: "auto_de_infracao",
  document_id: "auto-0007",
  scope_effective: "estrita",
  reasons: [{ type: "novo_documento" }],
  ingestion_job_id: "job-1",
  created_at: "2024-01-01T00:00:00Z",
};

const SAMPLE_DIGEST = {
  email_id: "carolina:job-1",
  user_id: "carolina",
  ingestion_job_id: "job-1",
  notification_ids: [5],
  rendered_body: "Você tem 1 novo(s) documento(s):\n- auto_de_infracao auto-0007",
  created_at: "2024-01-01T00:00:00Z",
};

function jsonResponse(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

function buildFetchMock(
  options: {
    scope?: { scope: string | null };
    notifications?: unknown[];
    digests?: unknown[];
  } = {},
) {
  const scope = options.scope ?? { scope: null };
  const notifications = options.notifications ?? [];
  const digests = options.digests ?? [];

  return vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    if (url.includes("/opened")) {
      return Promise.resolve(jsonResponse({ notification_id: 5, opened: true }));
    }
    if (url.includes("/notification-scope")) {
      if (init?.method === "PUT") {
        const body = JSON.parse((init.body as string) ?? "{}") as { scope: string };
        return Promise.resolve(jsonResponse({ scope: body.scope }));
      }
      return Promise.resolve(jsonResponse(scope));
    }
    if (url.includes("/email-digests")) {
      return Promise.resolve(jsonResponse(digests));
    }
    if (url.includes("/notifications")) {
      return Promise.resolve(jsonResponse(notifications));
    }
    return Promise.resolve(jsonResponse({}));
  });
}

function renderPage() {
  render(
    <MemoryRouter initialEntries={["/notificacoes"]}>
      <Routes>
        <Route path="/notificacoes" element={<NotificationsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("NotificationsPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mostra o aviso de dados demo/fixture imediatamente", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));

    renderPage();

    expect(screen.getByLabelText(/aviso de dados demo/i)).toHaveTextContent(/demo/i);
  });

  it("sem escopo escolhido, mostra só o seletor obrigatório sem opção pré-marcada", async () => {
    vi.stubGlobal("fetch", buildFetchMock({ scope: { scope: null } }));

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/escolha o escopo das suas notificações/i)).toBeInTheDocument(),
    );

    const estrita = screen.getByRole("radio", { name: /estrita/i });
    const ampla = screen.getByRole("radio", { name: /ampla/i });
    expect(estrita).not.toBeChecked();
    expect(ampla).not.toBeChecked();
    expect(screen.queryByLabelText(/lista de notificações/i)).not.toBeInTheDocument();
  });

  it("escolher escopo libera a lista de notificações e prévias", async () => {
    const fetchMock = buildFetchMock({
      scope: { scope: null },
      notifications: [SAMPLE_NOTIFICATION],
      digests: [SAMPLE_DIGEST],
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/escolha o escopo das suas notificações/i)).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("radio", { name: /estrita/i }));
    fireEvent.click(screen.getByRole("button", { name: /confirmar escopo/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/v1/users/carolina/notification-scope",
        expect.objectContaining({ method: "PUT" }),
      ),
    );

    await waitFor(() =>
      expect(
        within(screen.getByLabelText(/lista de notificações/i)).getByText(/auto_de_infracao/i),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/você tem 1 novo/i)).toBeInTheDocument();
  });

  it("lista renderiza notificações e prévias de digest quando o escopo já foi escolhido", async () => {
    vi.stubGlobal(
      "fetch",
      buildFetchMock({
        scope: { scope: "ampla" },
        notifications: [SAMPLE_NOTIFICATION],
        digests: [SAMPLE_DIGEST],
      }),
    );

    renderPage();

    await waitFor(() =>
      expect(
        within(screen.getByLabelText(/lista de notificações/i)).getByText(/auto-0007/i),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/você tem 1 novo/i)).toBeInTheDocument();
  });

  it("clicar numa notificação chama o endpoint de abertura", async () => {
    const fetchMock = buildFetchMock({
      scope: { scope: "estrita" },
      notifications: [SAMPLE_NOTIFICATION],
      digests: [],
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    const link = await screen.findByRole("link", { name: /ver documento/i });
    fireEvent.click(link);

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/v1/notifications/5/opened",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});
