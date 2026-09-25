import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { SessionProvider, useSession } from "./features/auth/SessionContext";
import { DemoDataProvider } from "./features/demo/DemoDataContext";
import { NotificationsProvider } from "./features/notifications/NotificationsContext";
import { ComingSoonPage } from "./pages/ComingSoonPage";
import { ExplorePage } from "./pages/ExplorePage";
import { FamiliesPage } from "./pages/FamiliesPage";
import { FamilyPage } from "./pages/FamilyPage";
import { LoginPage } from "./pages/LoginPage";
import { MyProcessesPage } from "./pages/MyProcessesPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { PersonaPage } from "./pages/PersonaPage";
import { ProductNotificationsPage } from "./pages/ProductNotificationsPage";
import { ProcessoPage } from "./pages/ProcessoPage";
import { RelationsMapPage } from "./pages/RelationsMapPage";
import { SearchPage } from "./pages/SearchPage";
import { OpinionPage } from "./pages/OpinionPage";

export function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <SessionProvider>
        <DemoDataProvider>
          <NotificationsProvider>
            <Routes>
            <Route path="/" element={<EntryRedirect />} />
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RequireSession />}>
              <Route path="/escolher-perfil" element={<PersonaPage />} />
              <Route element={<RequirePersona />}>
                <Route element={<AppShell />}>
                  <Route path="/explorar" element={<ExplorePage />} />
                  <Route path="/meus-processos" element={<MyProcessesPage />} />
                  <Route path="/familias" element={<FamiliesPage />} />
                  <Route path="/mapas-relacoes" element={<RelationsMapPage />} />
                  <Route path="/parecer-conclusivo" element={<OpinionPage />} />
                  <Route path="/notificacoes" element={<ProductNotificationsPage />} />
                  <Route path="/documents/:familyId" element={<FamilyPage />} />
                  <Route path="/processos/:processoId" element={<ProcessoPage />} />
                  <Route path="/meu-perfil" element={<ComingSoonPage title="Meu perfil" description="Preferências da usuária e da persona ativa." />} />
                  <Route path="/configuracoes" element={<ComingSoonPage title="Configurações" description="Preferências do CapiWatt Lens." />} />
                </Route>
              </Route>
            </Route>
            <Route path="/consulta-api" element={<SearchPage />} />
            <Route path="/integracoes/notificacoes" element={<NotificationsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </NotificationsProvider>
        </DemoDataProvider>
      </SessionProvider>
    </BrowserRouter>
  );
}

function EntryRedirect() {
  const { user, activePersona } = useSession();
  if (!user) return <Navigate to="/login" replace />;
  if (!activePersona) return <Navigate to="/escolher-perfil" replace />;
  return <Navigate to="/explorar" replace />;
}

function RequireSession() {
  return useSession().user ? <Outlet /> : <Navigate to="/login" replace />;
}

function RequirePersona() {
  return useSession().activePersona ? <Outlet /> : <Navigate to="/escolher-perfil" replace />;
}

export default App;
