import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExplorePage } from "./ExplorePage";
import { FamilyPage } from "./FamilyPage";

const searchEnvelope = {
  request_id: "request-35",
  data_mode: "demo",
  corpus_version: "demo-v1",
  model_version: "fixture-demo",
  ranking_version: "demo-ranking-v1",
  results: [
    {
      family_id: "fam-auto-0007",
      face: {
        document_version: "docver-auto-0007-v2",
        version_date: "2024-04-18",
        document_type: "auto_de_infracao",
        document_id: "auto-0007",
        processo_numero: "48500.001234/2024-11",
      },
      matched_chunks: [
        {
          document_version: "docver-auto-0007-v2",
          excerpt: "versao retificada com periodo corrigido",
          score: 0.91,
          is_latest: true,
        },
      ],
    },
  ],
};

afterEach(() => vi.unstubAllGlobals());

function renderPage(path = "/explorar") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/explorar" element={<ExplorePage />} />
        <Route path="/documents/:familyId" element={<FamilyPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ExplorePage integrada", () => {
  it("abre em uma home sem ranking antes de uma pesquisa", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /ainda não há uma pesquisa/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();
  });

  it("mostra resultados e metadados recebidos do backend", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(searchEnvelope)));

    renderPage("/explorar?q=auto%20de%20infra%C3%A7%C3%A3o%20retificado");

    expect(screen.getByLabelText(/carregando ranking/i)).toBeInTheDocument();
    expect(await screen.findByText("48500.001234/2024-11")).toBeInTheDocument();
    expect(screen.getByText("auto-0007 · fam-auto-0007")).toBeInTheDocument();
    expect(screen.getByText("versao retificada com periodo corrigido")).toBeInTheDocument();
    expect(screen.getAllByText("91%").length).toBeGreaterThan(0);
  });

  it("abre a família documental com o trecho da busca", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/v1/search") return jsonResponse(searchEnvelope);
      if (url.startsWith("/v1/documents/fam-auto-0007/graph")) {
        return jsonResponse({ node_id: "fam-auto-0007", node_kind: "family", edges: [] });
      }
      if (url.startsWith("/v1/documents/fam-auto-0007")) {
        return jsonResponse({
          family_id: "fam-auto-0007",
          document_id: "auto-0007",
          document_type: "auto_de_infracao",
          processo_numero: "48500.001234/2024-11",
          versions: [{ document_version: "docver-auto-0007-v2", version_date: "2024-04-18", version_date_source: "publication" }],
          selected_version: {
            document_version: "docver-auto-0007-v2",
            version_date: "2024-04-18",
            version_date_source: "publication",
            text: "Documento com versao retificada com periodo corrigido.",
          },
        });
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage("/explorar?q=auto%20de%20infra%C3%A7%C3%A3o%20retificado");
    await screen.findByText("48500.001234/2024-11");
    fireEvent.click(screen.getByRole("button", { name: /1 documento-chave/i }));
    fireEvent.click(screen.getByRole("button", { name: /abrir auto-0007/i }));

    expect(await screen.findByRole("heading", { name: /auto de infracao/i })).toBeInTheDocument();
    expect(screen.getByText(/trecho da busca/i)).toBeInTheDocument();
  });

  it("envia feedback com o request e a família retornados", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(searchEnvelope))
      .mockResolvedValueOnce(
        jsonResponse({ id: 1, request_id: "request-35", family_id: "fam-auto-0007", vote: "up", created_at: "2026-09-25" }),
      );
    vi.stubGlobal("fetch", fetchMock);

    renderPage("/explorar?q=auto%20de%20infra%C3%A7%C3%A3o%20retificado");
    await screen.findByText("48500.001234/2024-11");
    fireEvent.click(screen.getByRole("button", { name: /votar positivamente/i }));

    expect(await screen.findByText(/obrigado pelo feedback/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith("/v1/feedback", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ request_id: "request-35", family_id: "fam-auto-0007", vote: "up" }),
    })));
  });
});

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}
