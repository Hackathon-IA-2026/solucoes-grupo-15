import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mostra o status do backend e do ai quando o health check responde", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ backend: "ok", ai: "ok" }),
      }),
    );

    render(<App />);

    await waitFor(() => expect(screen.getByText(/backend: ok, ai: ok/i)).toBeInTheDocument());
  });

  it("mostra um estado de erro quando o health check falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network error")));

    render(<App />);

    await waitFor(() =>
      expect(screen.getByText(/não foi possível consultar o backend/i)).toBeInTheDocument(),
    );
  });
});
