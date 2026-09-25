import { AlertTriangle, Bell, Check, ChevronDown, Database, LoaderCircle, LogOut, Menu, RefreshCw, RotateCcw, Search, Settings, UserRound, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useSession } from "../../features/auth/SessionContext";
import { useDemoData } from "../../features/demo/DemoDataContext";
import { useNotifications } from "../../features/notifications/NotificationsContext";
import { Brand } from "./Brand";

export function Topbar({ menuOpen, onToggleMenu }: { menuOpen: boolean; onToggleMenu: () => void }) {
  const navigate = useNavigate();
  const { user, logout } = useSession();
  const demoData = useDemoData();
  const notificationState = useNotifications();
  const [accountOpen, setAccountOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationOpenError, setNotificationOpenError] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState(false);
  const [globalQuery, setGlobalQuery] = useState("");
  const unread = notificationState.kind === "ready"
    ? notificationState.notifications.filter((notification) => !notification.opened)
    : [];

  function submitGlobalSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = globalQuery.trim();
    navigate(query ? `/explorar?q=${encodeURIComponent(query)}` : "/explorar");
  }

  function handleLogout() {
    logout();
    navigate("/login");
  }

  async function openNotification(notificationId: number, familyId: string) {
    setNotificationOpenError(false);
    try {
      await notificationState.openNotification(notificationId);
      setNotificationsOpen(false);
      navigate(`/documents/${encodeURIComponent(familyId)}`);
    } catch {
      setNotificationOpenError(true);
    }
  }

  async function confirmReset() {
    setResetting(true);
    setResetError(false);
    try {
      await notificationState.resetDemo();
      setResetDialogOpen(false);
      navigate("/explorar");
    } catch {
      setResetError(true);
    } finally {
      setResetting(false);
    }
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
        <DemoStatus state={demoData.kind} onRetry={demoData.retry} />
        <div className="notification-control">
          <button className={`notification-button ${unread.length ? "has-unread" : notificationState.kind === "ready" ? "all-read" : ""}`} type="button" aria-label={`Notificações, ${unread.length} não lidas`} aria-expanded={notificationsOpen} onClick={() => { setNotificationsOpen((open) => !open); setAccountOpen(false); }}>
            <Bell size={21} />
            <span aria-hidden="true" />
          </button>
          {notificationsOpen && (
            <section className="notification-popover" aria-label="Notificações não lidas">
              <header><div><strong>Notificações</strong><span>{unread.length ? `${unread.length} não lida${unread.length === 1 ? "" : "s"}` : notificationState.kind === "ready" ? "Tudo em dia" : "Configuração necessária"}</span></div></header>
              {notificationState.kind === "loading" && <p className="popover-empty"><LoaderCircle size={17} /> Carregando notificações...</p>}
              {notificationState.kind === "scope-required" && <p className="popover-empty"><Bell size={17} /> Escolha o escopo para ativar as notificações.</p>}
              {notificationState.kind === "error" && <button className="popover-empty" type="button" onClick={() => void notificationState.retry()}><RefreshCw size={17} /> Tentar carregar novamente</button>}
              {notificationState.kind === "ready" && (unread.length ? <div className="popover-list">{unread.slice(0, 3).map((notification) => <button type="button" className="popover-notification" key={notification.id} onClick={() => void openNotification(notification.id, notification.family_id)}><span className="popover-notification-icon"><Bell size={15} /></span><span><strong>{notification.document_id ?? notification.document_version_id}</strong><small>{notification.document_type ?? "Documento"} · {formatDate(notification.created_at)}</small></span><Check size={15} /></button>)}</div> : <p className="popover-empty"><Check size={17} /> Não há atualizações pendentes.</p>)}
              {notificationOpenError && <p className="feedback-message error">Não foi possível abrir a notificação.</p>}
              <Link to="/notificacoes" onClick={() => setNotificationsOpen(false)}>Abrir central de notificações</Link>
            </section>
          )}
        </div>
        <div className="account-control">
          <button type="button" className="account-trigger" onClick={() => { setAccountOpen((open) => !open); setNotificationsOpen(false); }} aria-expanded={accountOpen}>
            <span className="avatar">{user?.initials ?? "CA"}</span>
            <span className="account-name"><strong>{user?.firstName ?? "Carol"}</strong><small>Advocacia regulatória</small></span>
            <ChevronDown size={16} />
          </button>
          {accountOpen && (
            <div className="account-menu" role="menu">
              <button type="button" role="menuitem" onClick={() => navigate("/meu-perfil")}><UserRound size={17} /> Meu perfil</button>
              <button type="button" role="menuitem" onClick={() => navigate("/configuracoes")}><Settings size={17} /> Configurações</button>
              <button type="button" role="menuitem" onClick={() => { setAccountOpen(false); setResetError(false); setResetDialogOpen(true); }}><RotateCcw size={17} /> Resetar demonstração</button>
              <button type="button" role="menuitem" onClick={handleLogout}><LogOut size={17} /> Sair</button>
            </div>
          )}
        </div>
      </div>
      {resetDialogOpen && (
        <div className="product-modal-backdrop" role="presentation" onMouseDown={() => !resetting && setResetDialogOpen(false)}>
          <section className="product-modal" role="dialog" aria-modal="true" aria-labelledby="reset-demo-title" onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" disabled={resetting} onClick={() => setResetDialogOpen(false)} aria-label="Fechar"><X /></button>
            <AlertTriangle size={28} />
            <h2 id="reset-demo-title">Resetar demonstração?</h2>
            <p>Notificações, leituras, escopo, feedbacks e buscas registradas serão apagados. O corpus documental e suas relações serão preservados.</p>
            {resetError && <p className="feedback-message error">Não foi possível resetar. Tente novamente.</p>}
            <div className="modal-actions">
              <button type="button" disabled={resetting} onClick={() => setResetDialogOpen(false)}>Cancelar</button>
              <button className="danger-outline-button" type="button" disabled={resetting} onClick={() => void confirmReset()}><RotateCcw size={17} /> {resetting ? "Resetando..." : "Confirmar reset"}</button>
            </div>
          </section>
        </div>
      )}
    </header>
  );
}

function DemoStatus({ state, onRetry }: { state: "idle" | "preparing" | "ready" | "error"; onRetry: () => void }) {
  if (state === "error") {
    return <button className="demo-status error" type="button" onClick={onRetry} aria-label="Modo demo indisponível. Tentar novamente"><RefreshCw size={14} /> Modo demo indisponível</button>;
  }
  if (state === "ready") {
    return <span className="demo-status ready"><Database size={14} /> Dados demo prontos</span>;
  }
  return <span className="demo-status preparing"><LoaderCircle size={14} /> Preparando dados demo</span>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}
