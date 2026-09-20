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

const SEARCH_ENVELOPE_WITH_ONE_RESULT = {
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
          document_version: "docver-auto-0007-v2",
          excerpt: "trecho novo",
          score: 0.9,
          is_latest: true,
        },
      ],
    },
  ],
};

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

  it("envia POST /v1/feedback com request_id, family_id e o voto ao clicar 👍", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/v1/search") {
        return Promise.resolve({
          ok: true,
          json: async () => SEARCH_ENVELOPE_WITH_ONE_RESULT,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({
          id: 1,
          request_id: "r1",
          family_id: "fam-auto-0007",
          vote: "up",
          created_at: "2026-09-20T00:00:00Z",
        }),
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /votar positivamente/i })).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: /votar positivamente/i }));

    await waitFor(() => expect(screen.getByText(/obrigado pelo feedback/i)).toBeInTheDocument());

    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/feedback",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ request_id: "r1", family_id: "fam-auto-0007", vote: "up" }),
      }),
    );
    expect(screen.getByRole("button", { name: /votar positivamente/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /votar negativamente/i })).toBeDisabled();
  });

  it("mostra mensagem de erro simples quando o envio de feedback falha, sem travar a página", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/v1/search") {
        return Promise.resolve({
          ok: true,
          json: async () => SEARCH_ENVELOPE_WITH_ONE_RESULT,
        });
      }
      return Promise.reject(new Error("network error"));
    });
    vi.stubGlobal("fetch", fetchMock);

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /votar negativamente/i })).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: /votar negativamente/i }));

    await waitFor(() =>
      expect(screen.getByText(/não foi possível registrar o feedback/i)).toBeInTheDocument(),
    );
    // A pagina de busca continua funcional - os botoes de voto nao ficam
    // travados num estado "submitting" permanente.
    expect(screen.getByRole("button", { name: /votar negativamente/i })).not.toBeDisabled();
  });
});
