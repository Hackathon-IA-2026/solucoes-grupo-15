import { BrowserRouter, Route, Routes } from "react-router-dom";

import { HealthBadge } from "./components/HealthBadge";
import { FamilyPage } from "./pages/FamilyPage";
import { ProcessoPage } from "./pages/ProcessoPage";
import { SearchPage } from "./pages/SearchPage";

/**
 * Shell de roteamento do frontend (TB1 Ticket 3, issue #19; Ticket 4,
 * issue #20 pendura a pagina real de familia; Ticket 5, issue #21
 * pendura a pagina de processo SEI).
 *
 * A busca (SearchPage) e a tela principal em "/" - substitui a tela de
 * health check que era o conteudo principal ate o Ticket 2.
 * "/documents/:familyId" leva a FamilyPage (cabecalho + linha do tempo
 * de versoes + texto com trechos destacados + painel "Relações").
 * "/processos/:processoId" leva a ProcessoPage (pecas do processo por
 * data + cadeia responde_a + o mesmo painel "Relações"). O health
 * check cruzado continua existindo, agora so como indicador discreto
 * de rodape (HealthBadge).
 */
export function App() {
  return (
    <BrowserRouter>
      <main>
        <h1>CapiWatt Lens</h1>
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/documents/:familyId" element={<FamilyPage />} />
          <Route path="/processos/:processoId" element={<ProcessoPage />} />
        </Routes>
      </main>
      <footer>
        <HealthBadge />
      </footer>
    </BrowserRouter>
  );
}

export default App;
