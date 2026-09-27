import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExplorePage } from "./ExplorePage";
import { FamilyPage } from "./FamilyPage";

// Resultado plano por chunk de POST /v1/search (#78/#96/#93).
function chunkResult(overrides: Record<string, unknown> = {}) {
  return {
    family_id: "fam-auto-0007",
    document_version: "docver-auto-0007-v2",
    chunk_id: "docver-auto-0007-v2#chunk-0002",
    chunk_index: 2,
    excerpt: "versao retificada com periodo corrigido",
    score: 0.91,
    localizador: "/data/documents/docver-auto-0007-v2/extracted.txt",
    document_type: "auto_de_infracao",
    document_id: "auto-0007",
    processo_numero: "48500.001234/2024-11",
    version_date: "2024-04-18",
    ...overrides,
  };
}

function envelope(results: unknown[], overrides: Record<string, unknown> = {}) {
  return {
    request_id: "request-35",
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

const searchEnvelope = envelope([chunkResult()]);

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

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
    expect(screen.getByRole("heading", { name: /explore por família/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();
  });

  it("mostra resultados e metadados recebidos do backend", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(searchEnvelope)));

    renderPage("/explorar?q=auto%20de%20infra%C3%A7%C3%A3o%20retificado");

    expect(screen.getByLabelText(/carregando ranking/i)).toBeInTheDocument();
    expect(await screen.findByText("48500.001234/2024-11")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /48500\.001234\/2024-11/i })).toHaveAttribute(
      "href",
      "/processos/48500.001234%2F2024-11",
    );
    expect(screen.getByText("auto-0007 · 1 documento localizado")).toBeInTheDocument();
    expect(screen.getByText("versao retificada com periodo corrigido")).toBeInTheDocument();
    expect(screen.getAllByText("91%").length).toBeGreaterThan(0);
  });

  it("agrupa os trechos retornados em um único conjunto por processo, sem repetir a peça", async () => {
    const enelAuto = chunkResult({
      family_id: "case1-enel-auto",
      document_version: "case1-enel-auto-2018",
      chunk_id: "case1-enel-auto-2018#chunk-0000",
      chunk_index: 0,
      document_id: "AI 0032/2018-SFE",
      processo_numero: "48500.004024/2017-80",
    });
    const mmgdEnvelope = envelope([
      enelAuto,
      chunkResult({
        family_id: "case1-enel-voto",
        document_version: "case1-enel-voto-2020",
        chunk_id: "case1-enel-voto-2020#chunk-0003",
        chunk_index: 3,
        document_type: "voto",
        document_id: "Voto DIR 48500.004024/2017-80",
        processo_numero: "48500.004024/2017-80",
        score: 0.8,
      }),
      chunkResult({
        family_id: "case1-cemig-voto",
        document_version: "case1-cemig-voto-2023",
        chunk_id: "case1-cemig-voto-2023#chunk-0001",
        chunk_index: 1,
        document_type: "voto",
        document_id: "Voto DIR 48500.000639/2019-07",
        processo_numero: "48500.000639/2019-07",
        score: 0.7,
      }),
      // Outro trecho da mesma peca ja listada: nao vira um segundo documento.
      { ...enelAuto, chunk_id: "case1-enel-auto-2018#chunk-0005", chunk_index: 5, score: 0.6 },
    ]);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(mmgdEnvelope)));

    renderPage("/explorar?q=precedentes%20sobre%20conex%C3%A3o%20de%20MMGD");

    expect(await screen.findByText("48500.004024/2017-80")).toBeInTheDocument();
    expect(screen.getByText("48500.000639/2019-07")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /2 documentos-chave/i })).toBeInTheDocument();
  });

  it("carrega mais trechos pelo cursor, mantendo a ordem dos processos já exibidos", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(envelope([chunkResult()], { total: 2, next_cursor: "cursor-2" })))
      .mockResolvedValueOnce(
        jsonResponse(
          envelope(
            [
              chunkResult({
                family_id: "case1-cemig-voto",
                document_version: "case1-cemig-voto-2023",
                chunk_id: "case1-cemig-voto-2023#chunk-0001",
                chunk_index: 1,
                document_id: "Voto DIR 48500.000639/2019-07",
                processo_numero: "48500.000639/2019-07",
                score: 0.5,
              }),
            ],
            { total: 2, next_cursor: null },
          ),
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    renderPage("/explorar?q=auto%20de%20infra%C3%A7%C3%A3o%20retificado");
    await screen.findByText("48500.001234/2024-11");
    fireEvent.click(screen.getByRole("button", { name: /carregar mais/i }));

    expect(await screen.findByText("48500.000639/2019-07")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/v1/search", expect.objectContaining({
      body: JSON.stringify({ query: "auto de infração retificado", cursor: "cursor-2" }),
    }));
    const processes = screen.getAllByRole("link", { name: /^48500\./ }).map((link) => link.textContent);
    expect(processes).toEqual(["48500.001234/2024-11", "48500.000639/2019-07"]);
    expect(screen.queryByRole("button", { name: /carregar mais/i })).not.toBeInTheDocument();
  });

  it("avisa quando o corpus mudou durante a navegação e oferece refazer a busca", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(envelope([chunkResult()], { total: 2, next_cursor: "cursor-2" })))
      .mockResolvedValueOnce(jsonResponse(envelope([chunkResult({ chunk_index: 7, chunk_id: "x#chunk-0007" })], { total: 2, stale_corpus: true })))
      .mockResolvedValueOnce(jsonResponse(envelope([chunkResult()], { request_id: "request-36" })));
    vi.stubGlobal("fetch", fetchMock);

    renderPage("/explorar?q=auto%20de%20infra%C3%A7%C3%A3o%20retificado");
    await screen.findByText("48500.001234/2024-11");
    fireEvent.click(screen.getByRole("button", { name: /carregar mais/i }));

    expect(await screen.findByText(/o corpus foi atualizado/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /refazer a busca/i }));

    await waitFor(() => expect(screen.queryByText(/o corpus foi atualizado/i)).not.toBeInTheDocument());
    expect(fetchMock).toHaveBeenLastCalledWith("/v1/search", expect.objectContaining({
      body: JSON.stringify({ query: "auto de infração retificado" }),
    }));
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

  it("envia feedback no trecho mais bem ranqueado do processo, com a chave vinda do próprio resultado", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(
          envelope([
            chunkResult(),
            chunkResult({ chunk_id: "docver-auto-0007-v2#chunk-0009", chunk_index: 9, score: 0.4, excerpt: "outro trecho" }),
          ]),
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse({ id: 1, request_id: "request-35", document_version: "docver-auto-0007-v2", chunk_index: 2, family_id: null, vote: "up", created_at: "2026-09-25" }),
      );
    vi.stubGlobal("fetch", fetchMock);

    renderPage("/explorar?q=auto%20de%20infra%C3%A7%C3%A3o%20retificado");
    await screen.findByText("48500.001234/2024-11");
    fireEvent.click(screen.getByRole("button", { name: /votar positivamente/i }));

    expect(await screen.findByText(/obrigado pelo feedback/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith("/v1/feedback", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ request_id: "request-35", document_version: "docver-auto-0007-v2", chunk_index: 2, vote: "up" }),
    })));
  });
});

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}
