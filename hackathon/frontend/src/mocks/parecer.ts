import type { OpinionData } from "../types/product";

export const mockOpinion: OpinionData = {
  title: "Fiscalização de solicitações de conexão de MMGD",
  processNumber: "48500.901433/2024-53",
  family: "Consumidores e Distribuição",
  theme: "Conexão de micro e minigeração distribuída",
  code: "PC-2026-0014",
  issuedAt: "24 de setembro de 2026",
  status: "Rascunho revisado",
  verdict: "Favorável com ressalvas",
  verdictSummary:
    "Os precedentes sustentam a responsabilização por descumprimento de prazos, com atenção à individualização das infrações e à dosimetria da penalidade.",
  situation:
    "A pesquisa examina a atuação fiscalizatória da ANEEL sobre atrasos e inadequações no atendimento a solicitações de conexão de MMGD por distribuidoras.",
  suggestedUnderstanding:
    "Há base regulatória e precedentes suficientes para sustentar a aplicação de penalidade quando comprovado o descumprimento dos prazos do PRODIST, preservada a análise das circunstâncias concretas e do nexo com cada infração.",
  attentionPoints: [
    "Confirmar a redação vigente dos dispositivos do PRODIST na data de cada fato.",
    "Separar o valor inicial da multa do valor mantido após recurso.",
    "Validar se o voto mais recente já corresponde ao resultado final da deliberação.",
    "Monitorar novas movimentações processuais dentro da janela de duas horas.",
  ],
  figures: [
    { label: "Precedentes prioritários", value: "3", tone: "green" },
    { label: "Documentos analisados", value: "10", tone: "blue" },
    { label: "Lacunas relevantes", value: "3", tone: "orange" },
    { label: "Período coberto", value: "2017–2026", tone: "purple" },
  ],
  confidence: 92,
  coverage: 87,
};
