import { FileCheck2, FolderKanban, Network, PanelLeftClose, PanelLeftOpen, Search, Sparkles, SwitchCamera } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";

import { useSession } from "../../features/auth/SessionContext";

const navigation = [
  { label: "Explorar", to: "/explorar", icon: Search },
  { label: "Meus Processos", to: "/meus-processos", icon: FolderKanban },
  { label: "Famílias documentais", to: "/familias", icon: Sparkles },
  { label: "Parecer demonstrativo", to: "/parecer", icon: FileCheck2 },
  { label: "Mapas e Relações", to: "/mapas-relacoes", icon: Network },
];

export function Sidebar({ open, collapsed, onNavigate, onToggleCollapsed }: { open: boolean; collapsed: boolean; onNavigate: () => void; onToggleCollapsed: () => void }) {
  const navigate = useNavigate();
  const { user } = useSession();
  return (
    <aside className={`${open ? "product-sidebar open" : "product-sidebar"} ${collapsed ? "collapsed" : ""}`}>
      <button type="button" className="sidebar-collapse" onClick={onToggleCollapsed} aria-expanded={!collapsed} aria-controls="primary-navigation" aria-label="Menu lateral" title={collapsed ? "Expandir menu lateral" : "Recolher menu lateral"}>{collapsed ? <PanelLeftOpen size={19} aria-hidden="true" /> : <PanelLeftClose size={19} aria-hidden="true" />}</button>
      <nav id="primary-navigation" aria-label="Navegação principal do produto">
        {navigation.map((item) => {
          const Icon = item.icon;
          return <NavLink key={item.to} to={item.to} onClick={onNavigate} title={collapsed ? item.label : undefined} className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}><Icon size={19} aria-hidden="true" /><span>{item.label}</span></NavLink>;
        })}
      </nav>
      <div className="persona-summary">
        <div className="persona-summary-row"><span className="persona-avatar" aria-hidden="true">{user?.initials ?? "CA"}</span><div><small>Persona ativa</small><strong>Advogados</strong><span>{user?.firstName ?? "Carol"}</span></div></div>
        <button type="button" onClick={() => navigate("/escolher-perfil")} title={collapsed ? "Trocar persona" : undefined}><SwitchCamera size={17} aria-hidden="true" /> <span>Trocar persona</span></button>
      </div>
    </aside>
  );
}
