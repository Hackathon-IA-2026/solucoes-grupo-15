import { Bell, Bolt, FileSearch, House, Search } from "lucide-react";
import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router-dom";

import { HealthBadge } from "./components/HealthBadge";
import { FamilyPage } from "./pages/FamilyPage";
import { NotificationsPage } from "./pages/NotificationsPage";
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
 *
 * "/notificacoes" (Ticket 8, issue #24) leva a NotificationsPage -
 * central de notificacoes + previa de digest de e-mail. Nao mexe em
 * "/" nem na SearchPage (a busca continua a tela principal, decisao
 * fechada no Ticket 3); so acrescenta um nav-link separado na topbar.
 */
export function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}

function AppLayout() {
  const location = useLocation();
  const isHome = location.pathname === "/";
  const isNotifications = location.pathname.startsWith("/notificacoes");

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link className="brand" to="/" aria-label="CapiWatt Lens - início">
            <span className="brand-mark" aria-hidden="true">
              <Bolt size={20} strokeWidth={2.5} />
            </span>
            <span>
              <strong>CapiWatt</strong>
              <small>Lens</small>
            </span>
          </Link>

          <nav className="main-nav" aria-label="Navegação principal">
            <Link className={isHome ? "nav-link active" : "nav-link"} to="/">
              <Search size={16} />
              Consulta
            </Link>
            <Link
              className={isNotifications ? "nav-link active" : "nav-link"}
              to="/notificacoes"
            >
              <Bell size={16} />
              Notificações
            </Link>
            {!isHome && !isNotifications && (
              <Link className="nav-link" to="/">
                <House size={16} />
                Nova consulta
              </Link>
            )}
          </nav>

          <div className="topbar-status">
            <FileSearch size={16} aria-hidden="true" />
            <span>Base documental</span>
            <HealthBadge />
          </div>
        </div>
      </header>

      <main className="app-content">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/documents/:familyId" element={<FamilyPage />} />
          <Route path="/processos/:processoId" element={<ProcessoPage />} />
          <Route path="/notificacoes" element={<NotificationsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
