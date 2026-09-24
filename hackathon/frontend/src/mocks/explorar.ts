import type { ExploreData } from "../types/product";

const documentSet = (prefix: string) => [
  { id: `${prefix}-ai`, type: "auto", label: "Auto de Infração", available: true },
  { id: `${prefix}-recurso`, type: "recurso", label: "Recurso", available: true },
  { id: `${prefix}-nt`, type: "nota", label: "Nota Técnica", available: true },
  { id: `${prefix}-voto`, type: "voto", label: "Voto", available: true },
];

export const mockExploreData: ExploreData = {
  query:
    "procure precedentes sobre fiscalização do atendimento às solicitações de conexão de microgeração e minigeração distribuída (MMGD)",
  filters: [
    "Todos",
    "Processos SEI",
    "Notas Técnicas",
    "Pareceres",
    "Acórdãos",
    "Normas",
    "Autos de Infração",
    "Juízos de Reconsideração",
  ],
  results: [
    {
      rank: 1,
      processNumber: "48500.004024/2017-80",
      adherence: 94,
      relevance: "Muito relevante",
      stance: "Precedente favorável",
      summary:
        "Fiscalização do atendimento às solicitações de conexão de MMGD pela Enel Ceará. Aborda prazos, procedimentos e aplicação de penalidades.",
      theme: "MMGD",
      period: "2017–2019",
      agency: "ANEEL",
      distributor: "Enel Ceará",
      tags: ["Fiscalização", "Conexão", "MMGD", "Distribuidora"],
      reasons: [
        "Trata diretamente de MMGD e atendimento a solicitações de conexão.",
        "Contém decisão da Diretoria e documentos processuais essenciais.",
        "Discute prazos, conduta da distribuidora e aplicação de penalidades.",
      ],
      documents: documentSet("4024"),
    },
    {
      rank: 2,
      processNumber: "48500.000639/2019-07",
      adherence: 87,
      relevance: "Muito relevante",
      stance: "Precedente favorável",
      summary:
        "Fiscalização de pedidos de conexão de MMGD e análise da conduta da Cemig. Discute critérios de acesso, prazos e tratamento de solicitações.",
      theme: "MMGD",
      period: "2019–2023",
      agency: "ANEEL",
      distributor: "Cemig Distribuição",
      tags: ["Conexão", "MMGD", "Fiscalização", "Prazos"],
      reasons: [
        "Analisa o mesmo tipo de fiscalização e o cumprimento de prazos.",
        "Apresenta voto e conclusão colegiada sobre as penalidades.",
        "Tem forte correspondência jurídica e regulatória com a consulta.",
      ],
      documents: documentSet("0639"),
    },
    {
      rank: 3,
      processNumber: "48500.901433/2024-53",
      adherence: 81,
      relevance: "Relevante",
      stance: "Em andamento",
      summary:
        "Apura irregularidades no atendimento a solicitações de conexão de MMGD pela Neoenergia Coelba, com foco em prazos, exigências e penalidades.",
      theme: "MMGD",
      period: "2024–atual",
      agency: "ANEEL",
      distributor: "Neoenergia Coelba",
      tags: ["Fiscalização", "Conexão", "MMGD", "Penalidades"],
      reasons: [
        "É o precedente mais recente do conjunto de referência.",
        "Inclui auto de infração, recurso e voto relacionados ao caso.",
        "A decisão recente amplia a cobertura temporal da pesquisa.",
      ],
      documents: documentSet("1433"),
    },
    {
      rank: 4,
      processNumber: "48500.003274/2020-11",
      adherence: 76,
      relevance: "Relevante",
      stance: "Precedente contrário",
      summary:
        "Fiscalização do processo de conexão de MMGD com divergência sobre interpretação normativa e responsabilidades da distribuidora.",
      theme: "MMGD",
      period: "2020–2022",
      agency: "ANEEL",
      distributor: "Distribuidora regional",
      tags: ["Conexão", "MMGD", "Interpretação normativa", "Fiscalização"],
      reasons: [
        "Oferece contraponto interpretativo útil para a estratégia jurídica.",
        "Tem aderência temática, embora com conjunto documental menos completo.",
      ],
      documents: documentSet("3274").slice(0, 3),
    },
  ],
  coverage: 82,
  coverageSummary:
    "Foram encontrados precedentes relevantes, com boa representatividade nos aspectos jurídicos e regulatórios.",
  metrics: [
    { label: "Jurídica", detail: "precedentes, decisões", value: 94, tone: "green" },
    { label: "Regulatória", detail: "normas, notas técnicas", value: 88, tone: "blue" },
    { label: "Técnica", detail: "procedimentos, critérios", value: 71, tone: "yellow" },
    { label: "Econômica", detail: "impactos, incentivos", value: 56, tone: "orange" },
  ],
  gaps: [
    {
      id: "gap-1",
      title: "Poucos precedentes recentes",
      detail: "Há poucos casos posteriores a 2023 sobre penalidades por atrasos na conexão de MMGD.",
    },
    {
      id: "gap-2",
      title: "Baixa diversidade de agentes",
      detail: "Faltam decisões envolvendo pequenas distribuidoras.",
    },
    {
      id: "gap-3",
      title: "Cobertura econômica limitada",
      detail: "Há pouca evidência sobre critérios objetivos de mensuração de danos aos agentes de MMGD.",
    },
  ],
};

export const mockGapEvidence = {
  processNumber: "48500.905054/2023-51",
  summary: "Evidência complementar recente sobre prazos e tratamento de solicitações de conexão.",
};
