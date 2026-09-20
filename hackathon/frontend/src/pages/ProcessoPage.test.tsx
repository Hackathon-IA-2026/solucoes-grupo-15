import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProcessoPage } from "./ProcessoPage";

const PROCESSO_ID = "48500.001234/2024-11";

const PROCESSO_BODY = {
  processo_id: PROCESSO_ID,
  pieces: [
    {
      family_id: "fam-defesa-0007",
      document_type: "peticao_defesa",
      document_id: "defesa-0007",
      version_date: "2024-03-20",
    },
    {
      family_id: "fam-auto-0007",
      document_type: "auto_de_infracao",
      document_id: "auto-0007",
      version_date: "2024-04-18",
    },
    {
      family_id: "fam-decisao-0007",
      document_type: "decisao",
      document_id: "decisao-0007",
      version_date: "2024-05-02",
    },
  ],
  responde_a: [
    {
      source_family_id: "fam-defesa-0007",
      target_family_id: "fam-auto-0007",
      evidence: {
        document_version: "docver-defesa-0007-v1",
        locator: "trecho inicial",
      },
    },
  ],
};

const EMPTY_GRAPH_BODY = { node_id: PROCESSO_ID, node_kind: "processo", edges: [] };

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body };
}

function mockProcessoAndGraphFetch(processoResponse: unknown) {
  return vi.fn().mockImplementation((url: string) => {
    if (url.includes("/graph")) {
      return Promise.resolve(jsonResponse(EMPTY_GRAPH_BODY));
    }
    return Promise.resolve(processoResponse);
  });
}

function renderProcessoPage(processoId = PROCESSO_ID) {
  render(
    <MemoryRouter initialEntries={[`/processos/${encodeURIComponent(processoId)}`]}>
      <Routes>
        <Route path="/processos/:processoId" element={<ProcessoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProcessoPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mostra o aviso de dados demo/fixture imediatamente", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));

    renderProcessoPage();

    expect(screen.getByLabelText(/aviso de dados demo/i)).toHaveTextContent(/demo/i);
  });

  it("mostra estado de carregamento e depois as peças ordenadas por data", async () => {
    vi.stubGlobal("fetch", mockProcessoAndGraphFetch(jsonResponse(PROCESSO_BODY)));

    renderProcessoPage();

    expect(screen.getByText(/carregando/i)).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText(`Processo ${PROCESSO_ID}`)).toBeInTheDocument());

    const items = screen.getAllByRole("listitem");
    const pieceLabels = items
      .map((item) => item.textContent ?? "")
      .filter((text) => text.includes("—"));

    expect(pieceLabels[0]).toContain("peticao_defesa — defesa-0007");
    expect(pieceLabels[1]).toContain("auto_de_infracao — auto-0007");
    expect(pieceLabels[2]).toContain("decisao — decisao-0007");
  });

  it("linka cada peça para /documents/{family_id}", async () => {
    vi.stubGlobal("fetch", mockProcessoAndGraphFetch(jsonResponse(PROCESSO_BODY)));

    renderProcessoPage();

    await waitFor(() =>
      expect(screen.getByText(/auto_de_infracao — auto-0007/i)).toBeInTheDocument(),
    );
    const link = screen.getByText(/auto_de_infracao — auto-0007/i).closest("a");
    expect(link).toHaveAttribute("href", "/documents/fam-auto-0007");
  });

  it("mostra a cadeia responde_a de forma visível", async () => {
    vi.stubGlobal("fetch", mockProcessoAndGraphFetch(jsonResponse(PROCESSO_BODY)));

    renderProcessoPage();

    await waitFor(() =>
      expect(
        screen.getByText(/fam-defesa-0007 responde a fam-auto-0007/i),
      ).toBeInTheDocument(),
    );
  });

  it("renderiza o painel de Relações centrado no processo", async () => {
    vi.stubGlobal("fetch", mockProcessoAndGraphFetch(jsonResponse(PROCESSO_BODY)));

    renderProcessoPage();

    await waitFor(() => expect(screen.getByLabelText("painel de relações")).toBeInTheDocument());
  });

  it("mostra mensagem clara quando o processo não é encontrado (404)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) }),
    );

    renderProcessoPage("00000.000000/9999-00");

    await waitFor(() =>
      expect(screen.getByText(/processo não encontrado/i)).toBeInTheDocument(),
    );
  });

  it("mostra estado de erro quando a requisição falha por rede", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    renderProcessoPage();

    await waitFor(() =>
      expect(screen.getByText(/não foi possível carregar o processo/i)).toBeInTheDocument(),
    );
  });
});
