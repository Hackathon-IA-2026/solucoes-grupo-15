import { BrowserRouter, Route, Routes } from "react-router-dom";

import { HealthBadge } from "./components/HealthBadge";
import { FamilyPlaceholderPage } from "./pages/FamilyPlaceholderPage";
import { SearchPage } from "./pages/SearchPage";

/**
 * Shell de roteamento do frontend (TB1 Ticket 3, issue #19).
 *
 * A busca (SearchPage) e a tela principal em "/" - substitui a tela de
 * health check que era o conteudo principal ate o Ticket 2.
 * "/documents/:familyId" fica registrada mas sem pagina real ainda (so
 * um placeholder - Ticket #20 pendura o conteudo la). O health check
 * cruzado continua existindo, agora so como indicador discreto de
 * rodape (HealthBadge).
 */
export function App() {
  return (
    <BrowserRouter>
      <main>
        <h1>CapiWatt Lens</h1>
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/documents/:familyId" element={<FamilyPlaceholderPage />} />
        </Routes>
      </main>
      <footer>
        <HealthBadge />
      </footer>
    </BrowserRouter>
  );
}

export default App;
