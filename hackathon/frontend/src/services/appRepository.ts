import { mockExploreData, mockGapEvidence } from "../mocks/explorar";
import { mockFamilies } from "../mocks/familias";
import { mockNotifications } from "../mocks/notificacoes";
import { mockOpinion } from "../mocks/parecer";
import { mockProcessDashboard } from "../mocks/processos";
import { appendSearchPage, searchDocuments, type SearchEnvelope, type SearchResult } from "../api/search";
import type {
  AppNotification,
  ExploreData,
  Family,
  OpinionData,
  ProcessDashboard,
} from "../types/product";

export interface AppRepository {
  searchPrecedents(query: string): Promise<ExploreData>;
  // Proxima pagina da mesma busca (cursor), acrescentada ao que ja foi carregado.
  loadMorePrecedents(data: ExploreData): Promise<ExploreData>;
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

  async loadMorePrecedents(data: ExploreData) {
    return data;
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

  override async loadMorePrecedents(data: ExploreData) {
    const pagination = data.pagination;
    if (!pagination || pagination.nextCursor === null) {
      return data;
    }
    const next = await searchDocuments(pagination.query, pagination.nextCursor);
    return mapSearchEnvelope(pagination.query, appendSearchPage(pagination.loaded, next));
  }

  override async findGapEvidence(query: string) {
    return this.searchPrecedents(query);
  }
}

/**
 * Traduz o envelope plano por chunk (issue #93) para o ranking por
 * processo da ExplorePage: os trechos sao agrupados por processo SEI na
 * ordem do backend (score decrescente), entao o primeiro trecho de cada
 * processo e o mais bem ranqueado e a ordem dos processos ja exibidos
 * nao muda quando a proxima pagina e acrescentada. Cada peca aparece uma
 * vez entre os documentos-chave, com todos os seus trechos casados.
 */
function mapSearchEnvelope(query: string, envelope: SearchEnvelope): ExploreData {
  const groupedByProcess = new Map<string, SearchResult[]>();
  for (const result of envelope.results) {
    const processKey = result.processo_numero ?? result.family_id;
    groupedByProcess.set(processKey, [...(groupedByProcess.get(processKey) ?? []), result]);
  }

  const results = [...groupedByProcess.entries()].map(([processNumber, processResults], index) => {
    const lead = processResults[0];
    const type = formatDocumentType(lead.document_type);
    const documents = new Map<string, SearchResult[]>();
    for (const chunk of processResults) {
      documents.set(chunk.family_id, [...(documents.get(chunk.family_id) ?? []), chunk]);
    }
    return {
      rank: index + 1,
      requestId: envelope.request_id,
      familyId: lead.family_id,
      feedbackChunk: { documentVersion: lead.document_version, chunkIndex: lead.chunk_index },
      processNumber,
      adherence: Math.round(lead.score * 100),
      relevance: lead.score >= 0.85 ? "Muito relevante" as const : "Relevante" as const,
      stance: "Resultado documental" as const,
      summary: lead.excerpt,
      theme: type,
      period: lead.version_date,
      agency: "ANEEL",
      distributor: lead.document_id,
      tags: [type, lead.document_version],
      reasons: processResults.map(
        (chunk) => `Trecho na versão ${chunk.document_version}: ${chunk.excerpt}`,
      ),
      documents: [...documents.values()].map((chunks) => ({
        id: chunks[0].family_id,
        familyId: chunks[0].family_id,
        type: chunks[0].document_type,
        label: chunks[0].document_id,
        available: true,
        matchedChunks: chunks.map((chunk) => ({ document_version: chunk.document_version, excerpt: chunk.excerpt })),
      })),
    };
  });
  const scores = results.map((result) => result.adherence);
  const average = scores.length
    ? Math.round(scores.reduce((total, score) => total + score, 0) / scores.length)
    : 0;

  return {
    query,
    pagination: {
      query,
      total: envelope.total,
      nextCursor: envelope.next_cursor,
      staleCorpus: envelope.stale_corpus,
      loaded: envelope,
    },
    filters: ["Todos", "Autos de Infração", "Decisões", "Normas", "Petições"],
    results,
    coverage: average,
    coverageSummary: results.length
      ? `${envelope.total} trecho(s) em ${results.length} processo(s) no corpus ${envelope.corpus_version}.`
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
