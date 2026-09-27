import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ExploreData } from "../../types/product";
import { CoveragePanel } from "./CoveragePanel";

afterEach(() => {
  cleanup();
});

function exploreData(overrides: Partial<ExploreData> = {}): ExploreData {
  return {
    query: "consulta de teste",
    results: [],
    coverage: 80,
    coverageSummary: "resumo",
    metrics: [{ label: "Métrica", detail: "detalhe", value: 80, tone: "green" }],
    gaps: [],
    ...overrides,
  };
}

describe("CoveragePanel", () => {
  it("limita a exibição da cobertura a 100% quando o backend retorna um valor maior", () => {
    render(<CoveragePanel data={exploreData({ coverage: 150 })} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.queryByText("150%")).not.toBeInTheDocument();
  });

  it("limita a exibição de cada métrica a 100% quando o backend retorna um valor maior", () => {
    render(
      <CoveragePanel
        data={exploreData({
          metrics: [{ label: "Melhor correspondência", detail: "detalhe", value: 120, tone: "blue" }],
        })}
      />,
    );
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.queryByText("120%")).not.toBeInTheDocument();
  });

  it("mantém valores normais (<=100) inalterados", () => {
    render(<CoveragePanel data={exploreData({ coverage: 80, metrics: [] })} />);
    expect(screen.getByText("80%")).toBeInTheDocument();
  });
});
