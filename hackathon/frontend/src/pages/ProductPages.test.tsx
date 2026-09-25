import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FamiliesPage } from "./FamiliesPage";
import { MyProcessesPage } from "./MyProcessesPage";
import { OpinionPage } from "./OpinionPage";
import { ProductNotificationsPage } from "./ProductNotificationsPage";
import { ProcessoPage } from "./ProcessoPage";
import { RelationsMapPage } from "./RelationsMapPage";

describe("páginas do produto", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lista o catalogo real e abre o detalhe integrado do processo", async () => {
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
      if (url.includes("/v1/processos/")) {
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
      if (url.includes("/graph")) {
        return new Response(JSON.stringify({ node_id: "48500.001234/2024-11", node_kind: "processo", edges: [] }), { status: 200 });
      }
      return new Response(null, { status: 404 });
    }));

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
    fireEvent.click(screen.getByRole("button", { name: /ver processo/i }));
    expect(await screen.findByRole("heading", { name: /processo 48500\.001234\/2024-11/i })).toBeInTheDocument();
    expect(screen.getByText(/peticao — defesa-0007/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cadeia de respostas/i)).toHaveTextContent("fam-defesa-0007");
  });

  it("lista e pesquisa famílias regulatórias", async () => {
    render(<FamiliesPage />);
    expect((await screen.findAllByText("Transição Energética", {}, { timeout: 1500 })).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText(/pesquisar famílias/i), { target: { value: "encargos setoriais" } });
    expect(screen.getAllByText("Tarifas e Encargos").length).toBeGreaterThan(0);
    expect(screen.queryByText("Consumidores e Distribuição")).not.toBeInTheDocument();
  });

  it("renderiza o parecer e alterna suas seções", async () => {
    render(<OpinionPage />);
    expect(await screen.findByText("Favorável com ressalvas", {}, { timeout: 1500 })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Evidências (10)" }));
    expect(screen.getByRole("heading", { name: "Evidências (10)" })).toBeInTheDocument();
  });

  it("marca uma notificação como lida", async () => {
    render(<ProductNotificationsPage />);
    expect(await screen.findByText("Novo voto juntado ao processo", {}, { timeout: 1500 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /não lidas \(3\)/i })).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /marcar como lida/i })[0]);
    expect(screen.getByRole("button", { name: /não lidas \(2\)/i })).toBeInTheDocument();
  });

  it("permite selecionar nós no mapa de relações", () => {
    render(<RelationsMapPage />);
    fireEvent.click(screen.getByRole("button", { name: /Voto da Diretoria/i }));
    expect(screen.getByText(/Fundamentos e conclusão submetidos/i)).toBeInTheDocument();
  });
});
