import { useState } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useDemoData } from "../../features/demo/DemoDataContext";
import { useRuntimeConfig } from "../../features/config/RuntimeConfigContext";

const COLLAPSE_KEY = "capiwatt-lens:sidebar-collapsed";

export function AppShell() {
  const demoData = useDemoData();
  const config = useRuntimeConfig();
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try { return window.localStorage.getItem(COLLAPSE_KEY) === "1"; } catch { return false; }
  });
  function toggleSidebar() {
    setSidebarCollapsed((collapsed) => {
      try { window.localStorage.setItem(COLLAPSE_KEY, collapsed ? "0" : "1"); } catch { /* preferência só em memória */ }
      return !collapsed;
    });
  }
  return (
    <div className={sidebarCollapsed ? "product-shell sidebar-collapsed" : "product-shell"}>
      <Topbar menuOpen={menuOpen} onToggleMenu={() => setMenuOpen((open) => !open)} />
      <Sidebar open={menuOpen} collapsed={sidebarCollapsed} onToggleCollapsed={toggleSidebar} onNavigate={() => setMenuOpen(false)} />
      {menuOpen && <button type="button" className="sidebar-scrim" aria-label="Fechar menu" onClick={() => setMenuOpen(false)} />}
      <main className="product-content">
        {config.cognito || demoData.kind === "ready"
          ? <Outlet />
          : demoData.kind === "error"
            ? <div className="product-empty"><h2>Não foi possível preparar os dados demonstrativos.</h2><button type="button" onClick={demoData.retry}>Tentar novamente</button></div>
            : <div className="skeleton wide" aria-label="Preparando dados demonstrativos" />}
      </main>
    </div>
  );
}
