import { fetchFamilies } from "../api/documents";
import { fetchNotifications, loadDemoUser } from "../api/notifications";
import { fetchOpinion } from "../api/opinion";
import { fetchProcessos } from "../api/processos";
import { appendSearchPage, searchDocuments, type SearchEnvelope, type SearchResult } from "../api/search";
import type {
  AppNotification,
  ExploreData,
  Family,
  OpinionData,
  ProcessDashboard,
  RecentActivity,
  TrackedProcess,
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

export class ApiAppRepository implements AppRepository {
  async searchPrecedents(query: string) {
    return mapSearchEnvelope(query, await searchDocuments(query));
  }

  async loadMorePrecedents(data: ExploreData) {
    const pagination = data.pagination;
    if (!pagination || pagination.nextCursor === null) {
      return data;
    }
    const next = await searchDocuments(pagination.query, pagination.nextCursor);
    return mapSearchEnvelope(pagination.query, appendSearchPage(pagination.loaded, next));
  }

  async findGapEvidence(query: string) {
    return this.searchPrecedents(query);
  }

  async getProcessDashboard(): Promise<ProcessDashboard> {
    const summaries = await fetchProcessos();
    const processes: TrackedProcess[] = summaries.map((p) => ({
      id: p.processo_id,
      subject: p.latest_document_id,
      agency: "ANEEL",
      origin: "Corpus demonstrativo",
      updatedAt: formatIsoDate(p.latest_movement_at),
      unread: 0,
      status: "Em análise" as const,
      tags: p.document_types,
      documents: p.document_types,
    }));
    const activity: RecentActivity[] = summaries.slice(0, 5).map((p, i) => ({
      id: `activity-${i + 1}`,
      label: `Andamento — ${p.latest_document_type}`,
      processNumber: p.processo_id,
      time: p.latest_movement_at,
    }));
    return { processes, activity };
  }

  async getFamilies(): Promise<Family[]> {
    const families = await fetchFamilies();
    return families.map((family) => ({
      id: family.family_id,
      name: family.document_id,
      description: `${formatDocumentType(family.document_type)}${family.processo_numero ? ` · Processo ${family.processo_numero}` : ""}`,
      documents: family.versions_count,
      status: `Atualizado em ${family.latest_version_date}`,
      tone: "blue" as const,
      icon: "landmark",
    }));
  }

  getOpinion(): Promise<OpinionData> {
    return fetchOpinion();
  }

  async getNotifications(): Promise<AppNotification[]> {
    const notifications = await fetchNotifications(loadDemoUser());
    return notifications.map((notification) => ({
      id: String(notification.id),
      title: notification.document_id ?? notification.document_version_id,
      reference: notification.family_id,
      description: notification.reasons.map((reason) => reason.type === "novo_documento"
        ? "Novo documento"
        : `Correlato: ${reason.relation_type}`).join(" · "),
      category: notification.document_type === "norma" ? "Norma" as const : "Processo SEI" as const,
      createdAt: notification.created_at,
      read: notification.opened,
    }));
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

function formatIsoDate(iso: string): string {
  const [date] = iso.split("T");
  const [year, month, day] = date.split("-");
  return `${day}/${month}/${year}`;
}

function formatDocumentType(value: string) {
  return value
    .split("_")
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export const appRepository: AppRepository = new ApiAppRepository();
