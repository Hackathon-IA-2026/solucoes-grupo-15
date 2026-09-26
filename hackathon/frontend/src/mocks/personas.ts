import type { Persona } from "../types/product";

export const mockPersonas: Persona[] = [
  {
    id: "advocacia",
    title: "Advogados",
    description: "Processos, normas e acompanhamento de casos.",
    image: "/assets/persona-advogados-v2.png",
    available: true,
  },
  {
    id: "pesquisa",
    title: "Pesquisadores",
    description: "Investigação de processos, normas e seus vínculos.",
    image: "/assets/persona-pesquisadores-v2.png",
    available: false,
  },
  {
    id: "engenharia",
    title: "Especialistas em regulação",
    description: "Fiscalização, processos, normas e acompanhamento regulatório.",
    image: "/assets/persona-regulacao-v2.png",
    available: false,
  },
];
