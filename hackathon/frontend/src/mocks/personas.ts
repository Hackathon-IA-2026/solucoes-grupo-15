import type { Persona } from "../types/product";

export const mockPersonas: Persona[] = [
  {
    id: "advocacia",
    title: "Advogados",
    label: "Advocacia regulatória",
    description: "Processos, normas, documentos e acompanhamento de casos.",
    image: "/assets/persona-advogados.png",
  },
  {
    id: "pesquisa",
    title: "Pesquisadores",
    label: "Pesquisa regulatória",
    description: "Busca de precedentes, documentos, processos e normas.",
    image: "/assets/persona-pesquisadores.png",
  },
  {
    id: "engenharia",
    title: "Agências reguladoras",
    label: "Regulação e fiscalização",
    description: "Fiscalização, processos, normas e acompanhamento regulatório.",
    image: "/assets/persona-engenheiros.png",
  },
];
