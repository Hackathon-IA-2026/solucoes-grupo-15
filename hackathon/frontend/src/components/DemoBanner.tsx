/**
 * Banner de aviso de dados demo/fixture (TB1 Ticket 4, issue #20).
 *
 * Extraido do aviso que ja existia so em SearchPage.tsx (Ticket 3,
 * issue #19) para ser reusado tambem na pagina de familia - o corpus
 * inteiro e fixture/demo e isso precisa ficar visivel em qualquer tela
 * que mostre dados dele.
 */
export function DemoBanner() {
  return (
    <p role="status" aria-label="aviso de dados demo">
      Dados de demonstração/fixture — este corpus é fictício, não representa
      casos reais e não deve ser tratado como tal.
    </p>
  );
}

export default DemoBanner;
