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

// Um resultado por chunk, no formato plano de POST /v1/search (#78/#96/#93).
function chunkResult(overrides: Record<string, unknown> = {}) {
  return {
    family_id: "fam-auto-0007",
    document_version: "docver-auto-0007-v2",
    chunk_id: "docver-auto-0007-v2#chunk-0004",
    chunk_index: 4,
    excerpt: "trecho novo",
    score: 0.9,
    localizador: "/data/documents/docver-auto-0007-v2/extracted.txt",
    document_type: "auto_de_infracao",
    document_id: "auto-0007",
    processo_numero: "48500.001234/2024-11",
    version_date: "2024-04-18",
    ...overrides,
  };
}

function envelope(overrides: Record<string, unknown> = {}) {
  const results = (overrides.results as unknown[] | undefined) ?? [chunkResult()];
  return {
    request_id: "r1",
    data_mode: "demo",
    corpus_version: "demo-v1",
    model_version: "fixture-demo",
    ranking_version: "demo-ranking-v1",
    results,
    total: results.length,
    next_cursor: null,
    stale_corpus: false,
    ...overrides,
  };
}

const SEARCH_ENVELOPE_WITH_ONE_RESULT = envelope();

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

  it("mostra um card por chunk casado, sem agrupar trechos da mesma peça, e a contagem vem de total", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () =>
          envelope({
            results: [
              chunkResult(),
              chunkResult({
                document_version: "docver-auto-0007-v1",
                chunk_id: "docver-auto-0007-v1#chunk-0001",
                chunk_index: 1,
                excerpt: "trecho antigo",
                score: 0.7,
                version_date: "2024-03-04",
              }),
            ],
            total: 34,
            next_cursor: "cursor-2",
          }),
      }),
    );

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);

    await waitFor(() => expect(screen.getByText("trecho novo")).toBeInTheDocument());
    expect(screen.getByText("trecho antigo")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.getByRole("heading", { name: /34 trechos encontrados/i })).toBeInTheDocument();
    expect(screen.getByText(/trecho na versão docver-auto-0007-v1/i)).toBeInTheDocument();
    expect(screen.getByText(/data da versão: 2024-03-04/i)).toBeInTheDocument();
  });

  it("carrega a próxima página pelo cursor e a acrescenta ao fim da lista, sem reordenar", async () => {
    const secondChunk = chunkResult({
      document_version: "docver-auto-0007-v1",
      chunk_id: "docver-auto-0007-v1#chunk-0001",
      chunk_index: 1,
      excerpt: "trecho antigo",
      score: 0.7,
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => envelope({ results: [chunkResult()], total: 2, next_cursor: "cursor-2" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => envelope({ results: [secondChunk], total: 2, next_cursor: null }),
      });
    vi.stubGlobal("fetch", fetchMock);

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);

    fireEvent.click(await screen.findByRole("button", { name: /carregar mais/i }));

    await waitFor(() => expect(screen.getByText("trecho antigo")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/v1/search",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ query: "auto de infração retificado", cursor: "cursor-2" }),
      }),
    );
    const excerpts = screen.getAllByRole("article").map((card) => card.querySelector(".evidence-item p")?.textContent);
    expect(excerpts).toEqual(["trecho novo", "trecho antigo"]);
    expect(screen.getByRole("heading", { name: /2 trechos encontrados/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /carregar mais/i })).not.toBeInTheDocument();
  });

  it("avisa quando o corpus mudou durante a navegação e oferece refazer a busca", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => envelope({ results: [chunkResult()], total: 2, next_cursor: "cursor-2" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () =>
          envelope({ results: [chunkResult({ excerpt: "trecho antigo" })], total: 2, stale_corpus: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => envelope({ request_id: "r2", results: [chunkResult({ excerpt: "trecho refeito" })] }),
      });
    vi.stubGlobal("fetch", fetchMock);

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);
    fireEvent.click(await screen.findByRole("button", { name: /carregar mais/i }));

    expect(await screen.findByText(/o corpus foi atualizado/i)).toBeInTheDocument();
    // A lista aberta continua sendo do corpus congelado: nada e injetado.
    expect(screen.getByText("trecho antigo")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /refazer a busca/i }));

    await waitFor(() => expect(screen.getByText("trecho refeito")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/v1/search",
      expect.objectContaining({ body: JSON.stringify({ query: "auto de infração retificado" }) }),
    );
    expect(screen.queryByText("trecho antigo")).not.toBeInTheDocument();
    expect(screen.queryByText(/o corpus foi atualizado/i)).not.toBeInTheDocument();
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

  it("envia POST /v1/feedback com request_id, a chave do chunk (document_version + chunk_index) e o voto ao clicar 👍", async () => {
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
          document_version: "docver-auto-0007-v2",
          chunk_index: 4,
          family_id: null,
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
        body: JSON.stringify({
          request_id: "r1",
          document_version: "docver-auto-0007-v2",
          chunk_index: 4,
          vote: "up",
        }),
      }),
    );
    expect(screen.getByRole("button", { name: /votar positivamente/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /votar negativamente/i })).toBeDisabled();
  });

  it("cada card vota no próprio trecho: o 👎 do segundo card vai para o chunk dele", async () => {
    const twoChunks = envelope({
      results: [
        chunkResult(),
        chunkResult({
          document_version: "docver-auto-0007-v1",
          chunk_id: "docver-auto-0007-v1#chunk-0001",
          chunk_index: 1,
          excerpt: "trecho antigo",
          score: 0.7,
        }),
      ],
    });
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) =>
      Promise.resolve({
        ok: true,
        json: async () => (String(input) === "/v1/search" ? twoChunks : { id: 1 }),
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderSearchPage();
    clickSuggestion(/auto de infração retificado/i);

    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: /votar negativamente/i })).toHaveLength(2),
    );
    fireEvent.click(screen.getAllByRole("button", { name: /votar negativamente/i })[1]);

    await waitFor(() => expect(screen.getByText(/obrigado pelo feedback/i)).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/feedback",
      expect.objectContaining({
        body: JSON.stringify({
          request_id: "r1",
          document_version: "docver-auto-0007-v1",
          chunk_index: 1,
          vote: "down",
        }),
      }),
    );
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
