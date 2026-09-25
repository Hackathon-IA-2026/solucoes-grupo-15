export type PersonaId = "advocacia" | "pesquisa" | "engenharia";

export type Persona = {
  id: PersonaId;
  title: string;
  label: string;
  description: string;
  image: string;
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
  matchedChunks?: Array<{
    document_version: string;
    excerpt: string;
    score: number;
    is_latest: boolean;
  }>;
};

export type RankedPrecedent = {
  rank: number;
  requestId?: string;
  familyId?: string;
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

export type ExploreData = {
  query: string;
  filters: string[];
  results: RankedPrecedent[];
  coverage: number;
  coverageSummary: string;
  metrics: CoverageMetric[];
  gaps: ResearchGap[];
};

export type TrackedProcess = {
  id: string;
  subject: string;
  agency: string;
  origin: string;
  updatedAt: string;
  unread: number;
  status: "Novo documento" | "Prazo próximo" | "Em análise" | "Arquivado";
  tags: string[];
  documents: string[];
  favorite?: boolean;
};

export type RecentActivity = {
  id: string;
  label: string;
  processNumber: string;
  time: string;
};

export type ProcessDashboard = {
  processes: TrackedProcess[];
  activity: RecentActivity[];
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
  confidence: number;
  coverage: number;
};

export type AppNotification = {
  id: string;
  title: string;
  reference: string;
  description: string;
  category: "Processo SEI" | "Norma" | "Consulta Pública" | "Parecer" | "Família";
  createdAt: string;
  read: boolean;
};
