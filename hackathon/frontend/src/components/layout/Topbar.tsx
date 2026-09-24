import { Bell, ChevronDown, LogOut, Menu, Search, Settings, UserRound, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useSession } from "../../features/auth/SessionContext";
import { Brand } from "./Brand";

export function Topbar({ menuOpen, onToggleMenu }: { menuOpen: boolean; onToggleMenu: () => void }) {
  const navigate = useNavigate();
  const { user, logout } = useSession();
  const [accountOpen, setAccountOpen] = useState(false);
  const [globalQuery, setGlobalQuery] = useState("");

  function submitGlobalSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = globalQuery.trim();
    navigate(query ? `/explorar?q=${encodeURIComponent(query)}` : "/explorar");
  }

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="product-topbar">
      <button className="topbar-menu-button" type="button" onClick={onToggleMenu} aria-label={menuOpen ? "Fechar menu" : "Abrir menu"}>{menuOpen ? <X size={22} /> : <Menu size={22} />}</button>
      <Brand />
      <form className="global-search" onSubmit={submitGlobalSearch}>
        <Search size={19} aria-hidden="true" />
        <input value={globalQuery} onChange={(event) => setGlobalQuery(event.target.value)} aria-label="Busca global" placeholder="Buscar normas, processos, pareceres, notas técnicas e mais..." />
        <kbd>Ctrl K</kbd>
      </form>
      <div className="topbar-actions">
        <Link className="notification-button" to="/notificacoes" aria-label="Notificações, 3 não lidas"><Bell size={21} /><span aria-hidden="true" /></Link>
        <div className="account-control">
          <button type="button" className="account-trigger" onClick={() => setAccountOpen((open) => !open)} aria-expanded={accountOpen}>
            <span className="avatar">{user?.initials ?? "CA"}</span>
            <span className="account-name"><strong>{user?.firstName ?? "Carol"}</strong><small>Advocacia regulatória</small></span>
            <ChevronDown size={16} />
          </button>
          {accountOpen && (
            <div className="account-menu" role="menu">
              <button type="button" role="menuitem" onClick={() => navigate("/meu-perfil")}><UserRound size={17} /> Meu perfil</button>
              <button type="button" role="menuitem" onClick={() => navigate("/configuracoes")}><Settings size={17} /> Configurações</button>
              <button type="button" role="menuitem" onClick={handleLogout}><LogOut size={17} /> Sair</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
