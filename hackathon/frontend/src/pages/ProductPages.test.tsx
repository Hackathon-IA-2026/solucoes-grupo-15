import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FamiliesPage } from "./FamiliesPage";
import { MyProcessesPage } from "./MyProcessesPage";
import { OpinionPage } from "./OpinionPage";
import { ProductNotificationsPage } from "./ProductNotificationsPage";
import { RelationsMapPage } from "./RelationsMapPage";

describe("páginas do produto", () => {
  it("filtra processos acompanhados e abre o detalhe", async () => {
    render(<MyProcessesPage />);
    expect(
      await screen.findByText("Fiscalização do atendimento às solicitações de conexão de MMGD", {}, { timeout: 1500 }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/buscar processos/i), { target: { value: "Cemig" } });
    expect(screen.getByText("Fiscalização de pedidos de conexão e conduta da distribuidora")).toBeInTheDocument();
    expect(screen.queryByText("Fiscalização do atendimento às solicitações de conexão de MMGD")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /ver processo/i }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Fiscalização de pedidos de conexão");
    fireEvent.click(screen.getByRole("button", { name: /abrir documentos/i }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Auto de Infração");
    fireEvent.click(screen.getByRole("button", { name: /parar de acompanhar/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByText("Fiscalização de pedidos de conexão e conduta da distribuidora")).not.toBeInTheDocument();
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
