import { FileCheck2, FolderKanban, Network, Search, Sparkles, SwitchCamera } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";

import { useSession } from "../../features/auth/SessionContext";

const navigation = [
  { label: "Explorar", to: "/explorar", icon: Search },
  { label: "Meus Processos", to: "/meus-processos", icon: FolderKanban },
  { label: "Famílias", to: "/familias", icon: Sparkles },
  { label: "Mapas e Relações", to: "/mapas-relacoes", icon: Network },
  { label: "Parecer Conclusivo", to: "/parecer-conclusivo", icon: FileCheck2 },
];

export function Sidebar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  const navigate = useNavigate();
  const { user } = useSession();
  return (
    <aside className={open ? "product-sidebar open" : "product-sidebar"}>
      <nav aria-label="Navegação principal do produto">
        {navigation.map((item) => {
          const Icon = item.icon;
          return <NavLink key={item.to} to={item.to} onClick={onNavigate} className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}><Icon size={19} /><span>{item.label}</span></NavLink>;
        })}
      </nav>
      <div className="persona-summary">
        <div className="persona-summary-row"><span className="persona-avatar">{user?.initials ?? "CA"}</span><div><small>Persona ativa</small><strong>Advocacia regulatória</strong><span>{user?.firstName ?? "Carol"}</span></div></div>
        <button type="button" onClick={() => navigate("/escolher-perfil")}><SwitchCamera size={17} /> Trocar persona</button>
      </div>
    </aside>
  );
}
