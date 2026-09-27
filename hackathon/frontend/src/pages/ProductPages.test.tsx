import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FamiliesPage } from "./FamiliesPage";
import { MyProcessesPage } from "./MyProcessesPage";
import { OpinionPage } from "./OpinionPage";
import { ProcessoPage } from "./ProcessoPage";
import { RelationsMapPage } from "./RelationsMapPage";

describe("páginas do produto", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/v1/processos") {
        return new Response(JSON.stringify([{
          processo_id: "48500.001234/2024-11",
          latest_movement_at: "2024-05-02",
          latest_document_type: "decisao",
          latest_document_id: "decisao-0007",
          pieces_count: 3,
          document_types: ["auto_de_infracao", "decisao", "peticao"],
        }]), { status: 200 });
      }
      if (url.includes("/v1/processos/") && !url.includes("/resultado")) {
        return new Response(JSON.stringify({
          processo_id: "48500.001234/2024-11",
          pieces: [
            { family_id: "fam-defesa-0007", document_type: "peticao", document_id: "defesa-0007", version_date: "2024-03-20" },
            { family_id: "fam-auto-0007", document_type: "auto_de_infracao", document_id: "auto-0007", version_date: "2024-04-18" },
            { family_id: "fam-decisao-0007", document_type: "decisao", document_id: "decisao-0007", version_date: "2024-05-02" },
          ],
          responde_a: [{ source_family_id: "fam-defesa-0007", target_family_id: "fam-auto-0007", evidence: null }],
        }), { status: 200 });
      }
      if (url.includes("/resultado")) {
        return new Response(JSON.stringify({
          title: "Fiscalização de solicitações",
          processNumber: "48500.901433/2024-53",
          family: "Consumidores",
          theme: "Conexão",
          code: "PC-2026-0014",
          issuedAt: "24 de setembro",
          status: "Rascunho",
          verdict: "Favorável com ressalvas",
          verdictSummary: "Os precedentes",
          situation: "A pesquisa",
          suggestedUnderstanding: "Há base",
          attentionPoints: ["Confirmar"],
          figures: [],
          confidence: 92,
          coverage: 87,
        }), { status: 200 });
      }
      if (url.includes("/v1/themes")) {
        return new Response(JSON.stringify([
          {
            id: "transicao",
            name: "Transição Energética",
            description: "Fontes renováveis e descarbonização.",
            tipos_processo: ["Outorga"],
            status: "Alta atividade",
          },
          {
            id: "tarifas",
            name: "Tarifas e Encargos",
            description: "Estrutura tarifária.",
            tipos_processo: ["Gestão Tarifária"],
            status: "Em alta",
          },
        ]), { status: 200 });
      }
      if (url.includes("/v1/families")) {
        return new Response(JSON.stringify([
          { family_id: "transicao", document_type: "transição_energética", versions_count: 1284 },
          { family_id: "tarifas", document_type: "tarifas_e_encargos", versions_count: 982 },
        ]), { status: 200 });
      }
      if (url.includes("/graph")) {
        return new Response(JSON.stringify({ node_id: "48500.001234/2024-11", node_kind: "processo", edges: [] }), { status: 200 });
      }
      return new Response(null, { status: 404 });
    }));
  });

  it("lista o catalogo real e abre o detalhe integrado do processo", async () => {

    render(
      <MemoryRouter initialEntries={["/meus-processos"]}>
        <Routes>
          <Route path="/meus-processos" element={<MyProcessesPage />} />
          <Route path="/processos/:processoId" element={<ProcessoPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("48500.001234/2024-11")).toBeInTheDocument();
    expect(screen.getByText("3 peças documentais")).toBeInTheDocument();
    expect(screen.getByText("02/05/2024")).toBeInTheDocument();
    const processLink = screen.getByRole("link", { name: /ver processo/i });
    expect(processLink).toHaveAttribute("href", "/processos/48500.001234%2F2024-11");
    fireEvent.click(processLink);
    expect(await screen.findByRole("heading", { name: /processo 48500\.001234\/2024-11/i })).toBeInTheDocument();
    expect(screen.getByText(/peticao — defesa-0007/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cadeia de respostas/i)).toHaveTextContent("fam-defesa-0007");
  });

  it("lista e pesquisa temas regulatórios sem contagem de documentos", async () => {
    render(<FamiliesPage />);
    expect((await screen.findAllByText("Transição Energética", {}, { timeout: 1500 })).length).toBeGreaterThan(0);
    expect(screen.queryByText(/\d+\s+documentos/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\d+\s+docs/i)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/pesquisar temas/i), { target: { value: "tarifas" } });
    expect(screen.getAllByText(/Tarifas e Encargos/i).length).toBeGreaterThan(0);
    expect(screen.queryByText("Consumidores e Distribuição")).not.toBeInTheDocument();
  });

  it("renderiza o parecer e alterna suas seções", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      title: "Parecer demonstrativo", processNumber: "48500.901433/2024-53", family: "Caso 1", theme: "MMGD",
      code: "DEMO-CASE1-MMGD", issuedAt: "2025-06-01", status: "Demonstração documental",
      verdict: "Trechos de precedentes para revisão", verdictSummary: "Trecho do voto Coelba",
      situation: "Trecho do voto Cemig", suggestedUnderstanding: "Trecho do voto Enel",
      attentionPoints: ["Consultar PDF"], figures: [], confidence: null, coverage: null,
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<OpinionPage />);
    expect(await screen.findByText("Trechos de precedentes para revisão")).toBeInTheDocument();
    expect(screen.getByText("Trecho do voto Coelba")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/v1/opinion");
    fireEvent.click(screen.getByRole("button", { name: "Evidências" }));
    expect(screen.getByRole("heading", { name: "Evidências" })).toBeInTheDocument();
  });

  it("limita confiança e cobertura do parecer a 100% quando o backend retorna um valor maior", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      title: "Parecer demonstrativo", processNumber: "48500.901433/2024-53", family: "Caso 1", theme: "MMGD",
      code: "DEMO-CASE1-MMGD", issuedAt: "2025-06-01", status: "Demonstração documental",
      verdict: "Trechos de precedentes para revisão", verdictSummary: "Trecho do voto Coelba",
      situation: "Trecho do voto Cemig", suggestedUnderstanding: "Trecho do voto Enel",
      attentionPoints: ["Consultar PDF"], figures: [], confidence: 150, coverage: 120,
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<OpinionPage />);
    expect(await screen.findByText("Trechos de precedentes para revisão")).toBeInTheDocument();
    expect(screen.getAllByText("100%").length).toBe(2);
    expect(screen.queryByText("150%")).not.toBeInTheDocument();
    expect(screen.queryByText("120%")).not.toBeInTheDocument();
  });

  it("mostra nós do grafo retornados pelo backend", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/v1/processos") return Promise.resolve(new Response(JSON.stringify([{ processo_id: "48500.004024/2017-80", latest_movement_at: "2020-01-01", latest_document_type: "voto", latest_document_id: "Voto Enel", pieces_count: 1, document_types: ["voto"] }]), { status: 200 }));
      if (path === "/v1/families") return Promise.resolve(new Response(JSON.stringify([{ family_id: "case1-enel-voto", document_id: "Voto Enel", document_type: "voto", processo_numero: "48500.004024/2017-80", versions_count: 1, latest_version_date: "2020-01-01" }]), { status: 200 }));
      if (path.startsWith("/v1/documents/")) return Promise.resolve(new Response(JSON.stringify({ node_id: "48500.004024/2017-80", node_kind: "processo", edges: [{ type: "pertence_ao_processo", origin: "explicit", status: "confirmed", neighbor_id: "case1-enel-voto", neighbor_kind: "family", evidence: null }] }), { status: 200 }));
      return Promise.resolve(new Response(null, { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<MemoryRouter><RelationsMapPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: /Voto Enel/i }));
    expect(screen.getByText("pertence_ao_processo")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/v1/documents/48500.004024%2F2017-80/graph");
  });
});
