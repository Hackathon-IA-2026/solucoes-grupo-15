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
    <aside className="demo-banner" role="status" aria-label="aviso de dados demo">
      <FlaskConical size={17} aria-hidden="true" />
      <span>
        <strong>Ambiente de demonstração.</strong> Este corpus é fictício, não representa casos
        reais e não deve ser tratado como tal.
      </span>
    </aside>
  );
}

export default DemoBanner;
import { FlaskConical } from "lucide-react";
