import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { SessionProvider, useSession } from "./features/auth/SessionContext";
import { ComingSoonPage } from "./pages/ComingSoonPage";
import { ExplorePage } from "./pages/ExplorePage";
import { FamilyPage } from "./pages/FamilyPage";
import { LoginPage } from "./pages/LoginPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { PersonaPage } from "./pages/PersonaPage";
import { ProcessoPage } from "./pages/ProcessoPage";
import { SearchPage } from "./pages/SearchPage";

export function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <SessionProvider>
        <Routes>
          <Route path="/" element={<EntryRedirect />} />
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireSession />}>
            <Route path="/escolher-perfil" element={<PersonaPage />} />
            <Route element={<RequirePersona />}>
              <Route element={<AppShell />}>
                <Route path="/explorar" element={<ExplorePage />} />
                <Route path="/meus-processos" element={<ComingSoonPage title="Meus Processos" description="Acompanhamento de processos, prazos e alertas em preparação." />} />
                <Route path="/familias" element={<ComingSoonPage title="Famílias" description="Navegação por macrotemas regulatórios em preparação." />} />
                <Route path="/mapas-relacoes" element={<ComingSoonPage title="Mapas e Relações" description="Visão conectada entre processos, documentos e normas em preparação." />} />
                <Route path="/parecer-conclusivo" element={<ComingSoonPage title="Parecer Conclusivo" description="Síntese jurídica estruturada em preparação." />} />
                <Route path="/notificacoes" element={<ComingSoonPage title="Notificações" description="Central de alertas processuais em preparação." />} />
                <Route path="/meu-perfil" element={<ComingSoonPage title="Meu perfil" description="Preferências da usuária e da persona ativa." />} />
                <Route path="/configuracoes" element={<ComingSoonPage title="Configurações" description="Preferências do CapiWatt Lens." />} />
              </Route>
            </Route>
          </Route>
          <Route path="/consulta-api" element={<SearchPage />} />
          <Route path="/integracoes/notificacoes" element={<NotificationsPage />} />
          <Route path="/documents/:familyId" element={<FamilyPage />} />
          <Route path="/processos/:processoId" element={<ProcessoPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
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
