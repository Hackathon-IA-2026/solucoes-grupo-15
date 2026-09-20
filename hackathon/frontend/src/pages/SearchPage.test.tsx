import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SearchPage } from "./SearchPage";

function renderSearchPage() {
  render(
    <MemoryRouter>
      <SearchPage />
    </MemoryRouter>,
  );
}

function clickSuggestion(name: RegExp) {
  fireEvent.click(screen.getByRole("button", { name }));
}

describe("SearchPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mostra o aviso de dados demo/fixture imediatamente", () => {
    renderSearchPage();

    expect(screen.getByLabelText(/aviso de dados demo/i)).toHaveTextContent(/demo/i);
  });

  it("mostra estado de carregamento enquanto a busca esta em voo", async () => {
    let resolveFetch: (value: unknown) => void = () => {};
    const pending = new Promise((resolve) => {
      resolveFetch = resolve;
    });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending));

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);

    await waitFor(() => expect(screen.getByText(/buscando/i)).toBeInTheDocument());

    resolveFetch({
      ok: true,
      json: async () => ({
        request_id: "r1",
        data_mode: "demo",
        corpus_version: "demo-v1",
        model_version: "fixture-demo",
        ranking_version: "demo-ranking-v1",
        results: [],
      }),
    });

    await waitFor(() =>
      expect(screen.getByText(/nenhum resultado para esta consulta demo/i)).toBeInTheDocument(),
    );
  });

  it("mostra os cards de resultado, com a face e as etiquetas de versão dos trechos", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          request_id: "r1",
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
              },
              matched_chunks: [
                {
                  document_version: "docver-auto-0007-v1",
                  excerpt: "trecho antigo",
                  score: 0.7,
                  is_latest: false,
                },
                {
                  document_version: "docver-auto-0007-v2",
                  excerpt: "trecho novo",
                  score: 0.9,
                  is_latest: true,
                },
              ],
            },
          ],
        }),
      }),
    );

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);

    await waitFor(() =>
      expect(screen.getByText(/auto_de_infracao — docver-auto-0007-v2/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/não é a versão mais recente/i)).toBeInTheDocument();
    expect(screen.getByText(/trecho na versão docver-auto-0007-v2 — versão mais recente/i)).toBeInTheDocument();
  });

  it("mostra mensagem de nenhum resultado quando results é uma lista vazia", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          request_id: "r1",
          data_mode: "demo",
          corpus_version: "demo-v1",
          model_version: "fixture-demo",
          ranking_version: "demo-ranking-v1",
          results: [],
        }),
      }),
    );

    renderSearchPage();
    clickSuggestion(/auditoria completa do processo/i);

    await waitFor(() =>
      expect(screen.getByText(/nenhum resultado para esta consulta demo/i)).toBeInTheDocument(),
    );
  });

  it("mostra estado de erro quando a busca falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);

    await waitFor(() =>
      expect(screen.getByText(/não foi possível concluir a busca/i)).toBeInTheDocument(),
    );
  });
});
