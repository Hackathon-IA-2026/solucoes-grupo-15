import { useState } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

const COLLAPSE_KEY = "capiwatt-lens:sidebar-collapsed";

export function AppShell() {
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
      <main className="product-content"><Outlet /></main>
    </div>
  );
}
