import type { Persona } from "../types/product";

export const mockPersonas: Persona[] = [
  {
    id: "advocacia",
    title: "Advogados",
    label: "Advocacia regulatória",
    description: "Processos, normas, documentos e acompanhamento de casos.",
    image: "/assets/persona-advogados-v2.png",
  },
  {
    id: "pesquisa",
    title: "Pesquisadores",
    label: "Pesquisa regulatória",
    description: "Investigação de processos, documentos, normas e seus vínculos.",
    image: "/assets/persona-pesquisadores-v2.png",
  },
  {
    id: "engenharia",
    title: "Especialistas em regulação",
    label: "Regulação e fiscalização",
    description: "Fiscalização, processos, normas e acompanhamento regulatório.",
    image: "/assets/persona-regulacao-v2.png",
  },
];
