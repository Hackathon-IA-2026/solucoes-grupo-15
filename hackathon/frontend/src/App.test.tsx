import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
  });

  it("conduz do login para a escolha de persona e para o shell do produto", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("heading", { name: /como você quer usar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /advogados/i })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: /continuar/i })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /advogados/i }));
    fireEvent.click(screen.getByRole("button", { name: /continuar/i }));

    await waitFor(() => expect(window.location.pathname).toBe("/explorar"));
    expect(screen.getByRole("navigation", { name: /navegação principal do produto/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /meus processos/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /notificações, 3 não lidas/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /ainda não há uma pesquisa/i })).toBeInTheDocument();
  });

  it("mantém sair dentro do menu da conta e encerra a sessão", async () => {
    window.localStorage.setItem("capiwatt-lens:mock-session", JSON.stringify({
      user: { id: "carolina", name: "Carolina", firstName: "Carol", initials: "CA", email: "carolina@capiwatt.demo" },
      activePersona: "advocacia",
    }));
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /Carol/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /sair/i }));

    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(screen.getByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  it("abre notificações no sino sem sair da página", async () => {
    window.localStorage.setItem("capiwatt-lens:mock-session", JSON.stringify({
      user: { id: "carolina", name: "Carolina", firstName: "Carol", initials: "CA", email: "carolina@capiwatt.demo" },
      activePersona: "advocacia",
    }));
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /notificações, 3 não lidas/i }));
    expect(screen.getByRole("region", { name: /notificações não lidas/i })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/explorar");
    fireEvent.click(screen.getByRole("button", { name: /marcar todas como lidas/i }));
    expect(screen.getByRole("button", { name: /notificações, 0 não lidas/i })).toBeInTheDocument();
  });
});
