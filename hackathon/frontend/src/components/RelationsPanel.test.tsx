import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RelationsPanel } from "./RelationsPanel";

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body };
}

function renderPanel(nodeId = "fam-auto-0007") {
  render(
    <MemoryRouter>
      <RelationsPanel nodeId={nodeId} />
    </MemoryRouter>,
  );
}

describe("RelationsPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("busca o grafo do nó recebido", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ node_id: "fam-auto-0007", node_kind: "family", edges: [] }));
    vi.stubGlobal("fetch", fetchMock);

    renderPanel("fam-auto-0007");

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/v1/documents/fam-auto-0007/graph"),
    );
  });

  it("mostra estado de carregamento enquanto a busca está em voo", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));

    renderPanel();

    expect(screen.getByText(/carregando relações/i)).toBeInTheDocument();
  });

  it("agrupa as arestas por tipo, cada grupo com seus vizinhos", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          node_id: "fam-auto-0007",
          node_kind: "family",
          edges: [
            {
              type: "pertence_ao_processo",
              origin: "explicit",
              status: "confirmed",
              neighbor_id: "48500.001234/2024-11",
              neighbor_kind: "processo",
              evidence: null,
            },
            {
              type: "responde_a",
              origin: "explicit",
              status: "confirmed",
              neighbor_id: "fam-defesa-0007",
              neighbor_kind: "family",
              evidence: {
                document_version: "docver-defesa-0007-v1",
                locator: "trecho inicial",
              },
            },
            {
              type: "referencia",
              origin: "explicit",
              status: "confirmed",
              neighbor_id: "fam-decisao-0007",
              neighbor_kind: "family",
              evidence: {
                document_version: "docver-decisao-0007-v1",
                locator: "trecho de manutenção da autuação",
              },
            },
          ],
        }),
      ),
    );

    renderPanel();

    await waitFor(() =>
      expect(screen.getByLabelText("relações do tipo pertence_ao_processo")).toBeInTheDocument(),
    );
    expect(screen.getByLabelText("relações do tipo responde_a")).toBeInTheDocument();
    expect(screen.getByLabelText("relações do tipo referencia")).toBeInTheDocument();

    expect(screen.getByText(/trecho inicial/i)).toBeInTheDocument();
  });

  it("linka vizinho família para /documents/{id} e vizinho processo para /processos/{id}", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          node_id: "fam-auto-0007",
          node_kind: "family",
          edges: [
            {
              type: "pertence_ao_processo",
              origin: "explicit",
              status: "confirmed",
              neighbor_id: "48500.001234/2024-11",
              neighbor_kind: "processo",
              evidence: null,
            },
            {
              type: "responde_a",
              origin: "explicit",
              status: "confirmed",
              neighbor_id: "fam-defesa-0007",
              neighbor_kind: "family",
              evidence: null,
            },
          ],
        }),
      ),
    );

    renderPanel();

    await waitFor(() => expect(screen.getByText("fam-defesa-0007")).toBeInTheDocument());

    const processoLink = screen.getByText("48500.001234/2024-11").closest("a");
    expect(processoLink).toHaveAttribute("href", "/processos/48500.001234%2F2024-11");

    const familyLink = screen.getByText("fam-defesa-0007").closest("a");
    expect(familyLink).toHaveAttribute("href", "/documents/fam-defesa-0007");
  });

  it("mostra mensagem quando não há nenhuma relação registrada", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ node_id: "fam-norma-1000", node_kind: "family", edges: [] })),
    );

    renderPanel("fam-norma-1000");

    await waitFor(() =>
      expect(screen.getByText(/nenhuma relação registrada/i)).toBeInTheDocument(),
    );
  });

  it("mostra mensagem clara quando o nó não é encontrado (404)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) }),
    );

    renderPanel("fam-inexistente");

    await waitFor(() =>
      expect(screen.getByText(/nó não encontrado/i)).toBeInTheDocument(),
    );
  });

  it("mostra estado de erro quando a requisição falha por rede", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    renderPanel();

    await waitFor(() =>
      expect(screen.getByText(/não foi possível carregar as relações/i)).toBeInTheDocument(),
    );
  });
});
