import type { Family } from "../types/product";

export const mockFamilies: Family[] = [
  { id: "transicao", name: "Transição Energética", description: "Fontes renováveis, descarbonização, hidrogênio, armazenamento e integração de sistemas.", documents: 1284, status: "Alta atividade", tone: "green", icon: "leaf" },
  { id: "tarifas", name: "Tarifas e Encargos", description: "Estrutura tarifária, encargos setoriais, modicidade tarifária e revisões tarifárias.", documents: 982, status: "Em alta", tone: "orange", icon: "coins" },
  { id: "mercado", name: "Mercado e Comercialização", description: "Ambiente de contratação, CCEE, comercialização, lastro e mecanismos de mercado.", documents: 1076, status: "Relevante", tone: "blue", icon: "chart" },
  { id: "regulacao", name: "Regulação e Governança", description: "Marco regulatório, competências institucionais, governança e processos decisórios.", documents: 1503, status: "Alta atividade", tone: "purple", icon: "landmark" },
  { id: "geracao", name: "Geração e Transmissão", description: "Planejamento, expansão, outorgas, operação e infraestrutura de transmissão.", documents: 1192, status: "Nova atualização", tone: "red", icon: "tower" },
  { id: "consumidores", name: "Consumidores e Distribuição", description: "Acesso, qualidade do serviço, modicidade tarifária e consumidores vulneráveis.", documents: 876, status: "Atualizada recentemente", tone: "cyan", icon: "users" },
];
