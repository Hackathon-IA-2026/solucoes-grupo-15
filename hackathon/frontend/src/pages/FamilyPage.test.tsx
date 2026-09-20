import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FamilyPage } from "./FamilyPage";

const DETAIL_BODY = {
  family_id: "fam-auto-0007",
  document_id: "auto-0007",
  document_type: "auto_de_infracao",
  processo_numero: "48500.001234/2024-11",
  versions: [
    {
      document_version: "docver-auto-0007-v2",
      version_date: "2024-04-18",
      version_date_source: "publication",
    },
    {
      document_version: "docver-auto-0007-v1",
      version_date: "2024-03-04",
      version_date_source: "publication",
    },
  ],
  selected_version: {
    document_version: "docver-auto-0007-v2",
    version_date: "2024-04-18",
    version_date_source: "publication",
    text: "Auto de Infracao no 0007/2024 (ficticio) - versao retificada. Corrige o periodo de apuracao.",
  },
};

const OLD_VERSION_DETAIL_BODY = {
  ...DETAIL_BODY,
  selected_version: {
    document_version: "docver-auto-0007-v1",
    version_date: "2024-03-04",
    version_date_source: "collection",
    text: "Auto de Infracao no 0007/2024 (ficticio). A fiscalizada e autuada por descumprimento.",
  },
};

// FamilyPage renderiza RelationsPanel (Ticket 5, issue #21), que faz
// sua propria chamada a GET /v1/documents/{familyId}/graph - resposta
// vazia por padrao, os testes deste arquivo nao exercitam o painel de
// relacoes (isso e coberto por RelationsPanel.test.tsx).
const EMPTY_GRAPH_BODY = { node_id: "fam-auto-0007", node_kind: "family", edges: [] };

function mockDocumentAndGraphFetch(
  detailByUrl: (url: string) => unknown,
): ReturnType<typeof vi.fn> {
  return vi.fn().mockImplementation((url: string) => {
    if (url.includes("/graph")) {
      return Promise.resolve(jsonResponse(EMPTY_GRAPH_BODY));
    }
    return Promise.resolve(jsonResponse(detailByUrl(url)));
  });
}

function renderFamilyPage(options?: {
  matchedChunks?: unknown[];
  familyId?: string;
}) {
  const familyId = options?.familyId ?? "fam-auto-0007";
  render(
    <MemoryRouter
      initialEntries={[
        {
          pathname: `/documents/${familyId}`,
          state: options?.matchedChunks ? { matchedChunks: options.matchedChunks } : undefined,
        },
      ]}
    >
      <Routes>
        <Route path="/documents/:familyId" element={<FamilyPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body };
}

describe("FamilyPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mostra o aviso de dados demo/fixture imediatamente", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));

    renderFamilyPage();

    expect(screen.getByLabelText(/aviso de dados demo/i)).toHaveTextContent(/demo/i);
  });

  it("mostra estado de carregamento e depois o cabeçalho da versão mais recente", async () => {
    vi.stubGlobal("fetch", mockDocumentAndGraphFetch(() => DETAIL_BODY));

    renderFamilyPage();

    expect(screen.getByText(/carregando/i)).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText("auto_de_infracao")).toBeInTheDocument());
    expect(screen.getByText(/identificador: auto-0007/i)).toBeInTheDocument();
    expect(screen.getByText(/processo: 48500\.001234\/2024-11/i)).toBeInTheDocument();
    expect(screen.getByText(/data \(publicação\): 2024-04-18/i)).toBeInTheDocument();
  });

  it("busca sem parametro de versao (pega a mais recente por padrao)", async () => {
    const fetchMock = mockDocumentAndGraphFetch(() => DETAIL_BODY);
    vi.stubGlobal("fetch", fetchMock);

    renderFamilyPage();

    await waitFor(() => expect(screen.getByText("auto_de_infracao")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith("/v1/documents/fam-auto-0007");
  });

  it("mostra mensagem clara quando a família não é encontrada (404)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) }),
    );

    renderFamilyPage({ familyId: "fam-inexistente" });

    await waitFor(() =>
      expect(screen.getByText(/família não encontrada/i)).toBeInTheDocument(),
    );
  });

  it("mostra estado de erro quando a requisição falha por rede", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    renderFamilyPage();

    await waitFor(() =>
      expect(screen.getByText(/não foi possível carregar o documento/i)).toBeInTheDocument(),
    );
  });

  it("destaca o trecho da busca quando matchedChunks aponta para a versão selecionada", async () => {
    vi.stubGlobal("fetch", mockDocumentAndGraphFetch(() => DETAIL_BODY));

    renderFamilyPage({
      matchedChunks: [
        {
          document_version: "docver-auto-0007-v2",
          excerpt: "versao retificada",
          score: 0.9,
          is_latest: true,
        },
      ],
    });

    await waitFor(() => expect(screen.getByText("versao retificada")).toBeInTheDocument());
    expect(screen.getByText("versao retificada").tagName).toBe("MARK");
    expect(screen.getByText(/trecho da busca — versão mais recente/i)).toBeInTheDocument();
  });

  it("troca de versão pela linha do tempo atualiza o texto exibido", async () => {
    const fetchMock = mockDocumentAndGraphFetch((url) =>
      url.includes("version=docver-auto-0007-v1") ? OLD_VERSION_DETAIL_BODY : DETAIL_BODY,
    );
    vi.stubGlobal("fetch", fetchMock);

    renderFamilyPage();

    await waitFor(() => expect(screen.getByText(/versao retificada/)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /2024-03-04/ }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/v1/documents/fam-auto-0007?version=docver-auto-0007-v1",
      ),
    );
    await waitFor(() =>
      expect(screen.getByText(/data \(coleta\): 2024-03-04/i)).toBeInTheDocument(),
    );
  });

  it("marca a linha do tempo quando há trecho casado numa versão não selecionada", async () => {
    vi.stubGlobal("fetch", mockDocumentAndGraphFetch(() => DETAIL_BODY));

    renderFamilyPage({
      matchedChunks: [
        {
          document_version: "docver-auto-0007-v1",
          excerpt: "descumprimento",
          score: 0.5,
          is_latest: false,
        },
      ],
    });

    await waitFor(() => expect(screen.getByText("auto_de_infracao")).toBeInTheDocument());

    const olderVersionItem = screen.getByRole("button", { name: /2024-03-04/ }).closest("li");
    expect(olderVersionItem).toHaveTextContent(/trecho relevante aqui/i);
  });

  it("funciona sem matchedChunks no state (acesso direto), sem nenhum destaque", async () => {
    vi.stubGlobal("fetch", mockDocumentAndGraphFetch(() => DETAIL_BODY));

    renderFamilyPage();

    await waitFor(() => expect(screen.getByText("auto_de_infracao")).toBeInTheDocument());
    expect(screen.queryByText(/trecho da busca/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/trecho relevante aqui/i)).not.toBeInTheDocument();
  });

  it("renderiza o painel de Relações (Ticket 5) buscando o grafo da família", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/graph")) {
        return Promise.resolve(
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
            ],
          }),
        );
      }
      return Promise.resolve(jsonResponse(DETAIL_BODY));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderFamilyPage();

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/v1/documents/fam-auto-0007/graph"),
    );
    await waitFor(() =>
      expect(screen.getByText("48500.001234/2024-11")).toBeInTheDocument(),
    );
    expect(screen.getByLabelText("painel de relações")).toBeInTheDocument();
  });
});
