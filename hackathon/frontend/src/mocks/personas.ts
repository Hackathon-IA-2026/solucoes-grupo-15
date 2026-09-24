import type { Persona } from "../types/product";

export const mockPersonas: Persona[] = [
  {
    id: "advocacia",
    title: "Advogados",
    label: "Advocacia regulatória",
    description: "Foco em direito, precedentes, normas e pareceres.",
    image: "/assets/persona-advogados.png",
  },
  {
    id: "pesquisa",
    title: "Pesquisadores",
    label: "Pesquisa regulatória",
    description: "Foco em busca aprofundada, análise documental e investigação.",
    image: "/assets/persona-pesquisadores.png",
  },
  {
    id: "engenharia",
    title: "Engenheiros",
    label: "Engenharia e operação",
    description: "Foco em análise técnica, infraestrutura, energia e operação.",
    image: "/assets/persona-engenheiros.png",
  },
];
