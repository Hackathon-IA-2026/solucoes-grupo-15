import { mockExploreData, mockGapEvidence } from "../mocks/explorar";
import { mockFamilies } from "../mocks/familias";
import { mockNotifications } from "../mocks/notificacoes";
import { mockOpinion } from "../mocks/parecer";
import { mockProcessDashboard } from "../mocks/processos";
import { searchDocuments, type SearchEnvelope } from "../api/search";
import type {
  AppNotification,
  ExploreData,
  Family,
  OpinionData,
  ProcessDashboard,
} from "../types/product";

export interface AppRepository {
  searchPrecedents(query: string): Promise<ExploreData>;
  findGapEvidence(query: string): Promise<ExploreData>;
  getProcessDashboard(): Promise<ProcessDashboard>;
  getFamilies(): Promise<Family[]>;
  getOpinion(): Promise<OpinionData>;
  getNotifications(): Promise<AppNotification[]>;
}

const wait = (delay = 420) => new Promise<void>((resolve) => window.setTimeout(resolve, delay));

export class MockAppRepository implements AppRepository {
  async searchPrecedents(query: string) {
    await wait(650);
    return { ...mockExploreData, query };
  }

  async findGapEvidence(query: string) {
    await wait(900);
    const evidenceResult = {
      ...mockExploreData.results[3],
      rank: 4,
      processNumber: mockGapEvidence.processNumber,
      adherence: 78,
      summary: mockGapEvidence.summary,
      stance: "Precedente favorável" as const,
    };
    return {
      ...mockExploreData,
      query,
      coverage: 88,
      results: [...mockExploreData.results.slice(0, 3), evidenceResult],
      gaps: mockExploreData.gaps.map((gap, index) =>
        index === 0 ? { ...gap, resolved: true } : gap,
      ),
    };
  }

  async getProcessDashboard() {
    await wait();
    return mockProcessDashboard;
  }

  async getFamilies() {
    await wait();
    return mockFamilies;
  }

  async getOpinion() {
    await wait();
    return mockOpinion;
  }

  async getNotifications() {
    await wait();
    return mockNotifications;
  }
}

export class ApiAppRepository extends MockAppRepository {
  override async searchPrecedents(query: string) {
    return mapSearchEnvelope(query, await searchDocuments(query));
  }

  override async findGapEvidence(query: string) {
    return this.searchPrecedents(query);
  }
}

function mapSearchEnvelope(query: string, envelope: SearchEnvelope): ExploreData {
  const results = envelope.results.map((result, index) => {
    const type = formatDocumentType(result.document_type);
    return {
      rank: index + 1,
      requestId: envelope.request_id,
      familyId: result.family_id,
      documentVersion: result.document_version,
      chunkIndex: result.chunk_index,
      processNumber: result.processo_numero ?? result.family_id,
      adherence: Math.round(result.score * 100),
      relevance: result.score >= 0.85 ? "Muito relevante" as const : "Relevante" as const,
      stance: "Resultado documental" as const,
      summary: result.excerpt,
      theme: type,
      period: result.version_date,
      agency: "ANEEL",
      distributor: result.document_id,
      tags: [type, result.document_version],
      reasons: [`Trecho na versão ${result.document_version}: ${result.excerpt}`],
      documents: [{
        id: result.family_id,
        familyId: result.family_id,
        type: result.document_type,
        label: result.document_id,
        available: true,
        matchedChunks: [{ document_version: result.document_version, excerpt: result.excerpt, score: result.score }],
      }],
    };
  });
  const scores = results.map((result) => result.adherence);
  const average = scores.length
    ? Math.round(scores.reduce((total, score) => total + score, 0) / scores.length)
    : 0;

  return {
    query,
    filters: ["Todos", "Autos de Infração", "Decisões", "Normas", "Petições"],
    results,
    coverage: average,
    coverageSummary: results.length
      ? `${results.length} trecho(s) retornado(s) pelo corpus ${envelope.corpus_version}.`
      : "Nenhum documento foi mapeado para esta consulta na fixture atual.",
    metrics: [
      { label: "Correspondência média", detail: "scores declarados na fixture", value: average, tone: "green" },
      { label: "Melhor correspondência", detail: "maior score retornado", value: Math.max(...scores, 0), tone: "blue" },
    ],
    gaps: [{
      id: "demo-corpus",
      title: "Cobertura limitada ao corpus demo",
      detail: "A ausência de resultados não significa ausência de precedentes fora desta fixture.",
    }],
  };
}

function formatDocumentType(value: string) {
  return value
    .split("_")
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export const appRepository: AppRepository = new ApiAppRepository();
