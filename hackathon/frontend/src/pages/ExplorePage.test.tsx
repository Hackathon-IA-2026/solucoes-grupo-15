import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ExplorePage } from "./ExplorePage";

function renderPage(path = "/explorar") {
  render(<MemoryRouter initialEntries={[path]}><ExplorePage /></MemoryRouter>);
}

describe("ExplorePage", () => {
  it("abre em uma home sem ranking antes de uma pesquisa", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /ainda não há uma pesquisa/i })).toBeInTheDocument();
    expect(screen.queryByText("48500.004024/2017-80")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeDisabled();
  });

  it("mostra o ranking MMGD e explica o primeiro precedente", async () => {
    renderPage("/explorar?q=MMGD");
    expect(screen.getByLabelText(/carregando ranking/i)).toBeInTheDocument();
    expect(await screen.findByText("48500.004024/2017-80", {}, { timeout: 2000 })).toBeInTheDocument();
    expect(screen.getByText("48500.000639/2019-07")).toBeInTheDocument();
    expect(screen.getByText("48500.901433/2024-53")).toBeInTheDocument();
    expect(screen.getByText(/trata diretamente de MMGD/i)).toBeInTheDocument();
  });

  it("abre a explicação do ranking e os documentos-chave", async () => {
    renderPage("/explorar?q=MMGD");
    await screen.findByText("48500.004024/2017-80", {}, { timeout: 2000 });
    fireEvent.click(screen.getByRole("button", { name: /como o ranking é calculado/i }));
    expect(screen.getByRole("dialog", { name: /como o ranking é calculado/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
    fireEvent.click(screen.getAllByRole("button", { name: /4 documentos-chave/i })[0]);
    expect(screen.getByRole("dialog", { name: /documentos-chave/i })).toHaveTextContent("Auto de Infração");
    expect(screen.getByRole("dialog", { name: /documentos-chave/i })).toHaveTextContent("Voto");
  });

  it("simula a busca de evidências e melhora a cobertura", async () => {
    renderPage("/explorar?q=MMGD");
    await screen.findByText("48500.004024/2017-80", {}, { timeout: 2000 });
    fireEvent.click(screen.getByRole("button", { name: /buscar evidências para preencher/i }));
    expect(screen.getByRole("button", { name: /buscando novas evidências/i })).toBeDisabled();
    expect(await screen.findByText(/nova evidência encontrada/i, {}, { timeout: 2500 })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("88%").length).toBeGreaterThan(0));
  });
});
