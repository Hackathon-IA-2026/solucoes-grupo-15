import type { SearchEnvelope } from "../api/search";
import type { ProcessoSummary } from "../api/processos";

export type PersonaId = "advocacia" | "pesquisa" | "engenharia";

export type Persona = {
  id: PersonaId;
  title: string;
  description: string;
  image: string;
  available: boolean;
};

export type SessionUser = {
  id: string;
  name: string;
  firstName: string;
  initials: string;
  email: string;
};

export type DocumentKey = {
  id: string;
  familyId?: string;
  type: string;
  label: string;
  available: boolean;
  // Trechos desta peca casados na busca, levados ao destaque da FamilyPage.
  matchedChunks?: Array<{
    document_version: string;
    excerpt: string;
  }>;
};

export type RankedPrecedent = {
  rank: number;
  requestId?: string;
  familyId?: string;
  // Chunk mais bem ranqueado do processo (o primeiro na ordem do backend):
  // alvo do voto de feedback, com a chave vinda do proprio resultado (#93).
  feedbackChunk?: { documentVersion: string; chunkIndex: number };
  processNumber: string;
  adherence: number;
  relevance: "Muito relevante" | "Relevante";
  stance: "Precedente favorável" | "Precedente contrário" | "Em andamento" | "Resultado documental";
  summary: string;
  theme: string;
  period: string;
  agency: string;
  distributor: string;
  tags: string[];
  reasons: string[];
  documents: DocumentKey[];
};

export type CoverageMetric = {
  label: string;
  detail: string;
  value: number;
  tone: "green" | "blue" | "yellow" | "orange";
};

export type ResearchGap = {
  id: string;
  title: string;
  detail: string;
  resolved?: boolean;
};

/**
 * Estado da paginacao por cursor de uma busca real (issue #93). ``loaded``
 * e o envelope acumulado de todas as paginas ja carregadas, para que a
 * proxima pagina seja reagrupada sem reordenar o que ja esta na tela.
 */
export type SearchPagination = {
  query: string;
  total: number;
  nextCursor: string | null;
  staleCorpus: boolean;
  loaded: SearchEnvelope;
};

export type ExploreData = {
  query: string;
  pagination?: SearchPagination;
  results: RankedPrecedent[];
  coverage: number;
  coverageSummary: string;
  metrics: CoverageMetric[];
  gaps: ResearchGap[];
};

export type ProcessDashboard = {
  processes: ProcessoSummary[];
};

export type Family = {
  id: string;
  name: string;
  description: string;
  documents: number;
  status: string;
  tone: "green" | "orange" | "blue" | "purple" | "red" | "cyan";
  icon: string;
};

export type OpinionData = {
  title: string;
  processNumber: string;
  family: string;
  theme: string;
  code: string;
  issuedAt: string;
  status: string;
  verdict: string;
  verdictSummary: string;
  situation: string;
  suggestedUnderstanding: string;
  attentionPoints: string[];
  figures: Array<{ label: string; value: string; tone: string }>;
  confidence: number | null;
  coverage: number | null;
};

export type AppNotification = {
  id: string;
  title: string;
  reference: string;
  description: string;
  category: "Processo SEI" | "Norma" | "Consulta Pública" | "Parecer" | "Tema";
  createdAt: string;
  read: boolean;
};
