import { useParams } from "react-router-dom";

/**
 * Rota /documents/:familyId registrada para o Ticket #20 (proximo)
 * ter onde pendurar a pagina de familia (cabecalho, linha do tempo de
 * versoes, texto com trechos etiquetados). Este Ticket (#19) so
 * registra a rota - nenhum conteudo real e implementado aqui.
 */
export function FamilyPlaceholderPage() {
  const { familyId } = useParams<{ familyId: string }>();

  return (
    <section aria-label="pagina de familia (em construção)">
      <h2>Página de família — em construção</h2>
      <p>family_id: {familyId}</p>
    </section>
  );
}

export default FamilyPlaceholderPage;
