import type { AppNotification } from "../types/product";

export const mockNotifications: AppNotification[] = [
  { id: "notification-1", title: "Novo voto juntado ao processo", reference: "SEI 48500.901433/2024-53", description: "O voto do processo acompanhado foi disponibilizado. A conclusão e os valores citados já podem ser revisados.", category: "Processo SEI", createdAt: "há 2 horas", read: false },
  { id: "notification-2", title: "Nova norma publicada", reference: "Resolução Normativa ANEEL nº 1.118/2026", description: "Publicada atualização sobre requisitos de conexão de geração distribuída.", category: "Norma", createdAt: "há 4 horas", read: false },
  { id: "notification-3", title: "Nova consulta pública aberta", reference: "CP ANEEL nº 021/2026", description: "Aberta consulta pública sobre aprimoramentos nas regras de comercialização de energia elétrica.", category: "Consulta Pública", createdAt: "há 6 horas", read: false },
  { id: "notification-4", title: "Novo parecer disponível", reference: "Parecer CapiWatt PC-2026-0014", description: "A síntese de precedentes de MMGD foi atualizada com o voto mais recente.", category: "Parecer", createdAt: "ontem, 16:42", read: true },
  { id: "notification-5", title: "Atualização de andamento", reference: "SEI 48500.900192/2024-25", description: "O processo foi movimentado para a área técnica da ANEEL.", category: "Processo SEI", createdAt: "ontem, 11:18", read: true },
  { id: "notification-6", title: "Atualização em família temática", reference: "Consumidores e Distribuição", description: "Foram adicionados quatro novos documentos à família.", category: "Família", createdAt: "12 set., 14:27", read: true },
];
