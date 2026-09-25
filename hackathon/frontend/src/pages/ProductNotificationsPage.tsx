import { ArrowUpRight, Bell, Check, FileText, Mail, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { NotificationReason, NotificationScope } from "../api/notifications";
import { PageHero } from "../components/layout/PageHero";
import { useNotifications } from "../features/notifications/NotificationsContext";

export function ProductNotificationsPage() {
  const navigate = useNavigate();
  const state = useNotifications();
  const [filter, setFilter] = useState<"Todas" | "Não lidas">("Todas");
  const [openError, setOpenError] = useState(false);

  const visible = useMemo(() => state.kind === "ready"
    ? state.notifications.filter((notification) => filter === "Todas" || !notification.opened)
    : [], [filter, state]);
  const unread = state.kind === "ready"
    ? state.notifications.filter((notification) => !notification.opened).length
    : 0;

  async function openNotification(notificationId: number, familyId: string) {
    setOpenError(false);
    try {
      await state.openNotification(notificationId);
      navigate(`/documents/${encodeURIComponent(familyId)}`);
    } catch {
      setOpenError(true);
    }
  }

  return (
    <div className="product-page">
      <PageHero
        icon={Bell}
        title="Notificações"
        description="Acompanhe os novos documentos gerados pelo corpus demonstrativo."
      />

      {state.kind === "scope-required" && <ScopePicker onChoose={state.chooseScope} />}
      {(state.kind === "idle" || state.kind === "loading") && <div className="skeleton notifications-skeleton" />}
      {state.kind === "error" && (
        <div className="product-empty">
          <Bell size={28} />
          <h3>Não foi possível carregar as notificações.</h3>
          <p>Confira os serviços locais e tente novamente.</p>
          <button className="yellow-button" type="button" onClick={() => void state.retry()}>
            <RefreshCw size={17} /> Tentar novamente
          </button>
        </div>
      )}
      {state.kind === "ready" && (
        <>
          <div className="segmented-control notifications-filters">
            <button type="button" className={filter === "Todas" ? "active" : ""} onClick={() => setFilter("Todas")}>Todas</button>
            <button type="button" className={filter === "Não lidas" ? "active" : ""} onClick={() => setFilter("Não lidas")}>Não lidas ({unread})</button>
          </div>
          {openError && <p className="feedback-message error">Não foi possível registrar a abertura. Tente novamente.</p>}
          <div className="notifications-layout">
            <section className="notification-stream" aria-label="lista de notificações">
              {visible.length === 0 ? (
                <div className="product-empty"><Check size={28} /><h3>Nenhuma notificação pendente.</h3><p>Novos documentos aparecerão aqui após uma ingestão.</p></div>
              ) : visible.map((notification) => (
                <article className={notification.opened ? "notification-item read" : "notification-item"} key={notification.id}>
                  <span className="notification-icon notification-processo-sei"><FileText size={22} /></span>
                  <div>
                    <h2>{notification.document_id ?? notification.document_version_id}</h2>
                    <strong>{formatDocumentType(notification.document_type ?? "documento")}</strong>
                    <ul className="notification-reasons">
                      {notification.reasons.map((reason, index) => <li key={index}>{formatReason(reason)}</li>)}
                    </ul>
                  </div>
                  <div className="notification-meta">
                    <span className="status-chip blue">Escopo {notification.scope_effective}</span>
                    <time>{formatDate(notification.created_at)}</time>
                    <button type="button" onClick={() => void openNotification(notification.id, notification.family_id)}>
                      <ArrowUpRight size={15} /> {notification.opened ? "Abrir documento" : "Abrir e marcar como lida"}
                    </button>
                  </div>
                </article>
              ))}
            </section>
            <aside className="summary-sidebar notifications-sidebar">
              <div className="notification-callout">
                <Bell size={28} />
                <h2>Escopo {state.scope}</h2>
                <p>{state.notifications.length} notificação(ões), {unread} não lida(s).</p>
              </div>
              <h3><Mail size={16} /> Prévia de e-mail</h3>
              {state.digests.length === 0 ? (
                <p>Nenhum digest foi gerado para esta ingestão.</p>
              ) : (
                <div className="email-digest-list">
                  {state.digests.map((digest) => <pre key={digest.email_id}>{digest.rendered_body}</pre>)}
                </div>
              )}
            </aside>
          </div>
        </>
      )}
    </div>
  );
}

function ScopePicker({ onChoose }: { onChoose: (scope: NotificationScope) => Promise<void> }) {
  const [selected, setSelected] = useState<NotificationScope | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    if (!selected) return;
    setSubmitting(true);
    try {
      await onChoose(selected);
    } catch {
      // O provider troca para o estado de erro compartilhado.
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="product-empty scope-picker" aria-label="escolha de escopo">
      <Bell size={28} />
      <h2>Escolha o escopo das notificações</h2>
      <p>Nenhuma opção é aplicada automaticamente.</p>
      <fieldset>
        <legend className="sr-only">Escopo de notificações</legend>
        <label className="scope-option"><input type="radio" name="product-notification-scope" checked={selected === "estrita"} onChange={() => setSelected("estrita")} /><span><strong>Estrita</strong> Apenas documentos novos.</span></label>
        <label className="scope-option"><input type="radio" name="product-notification-scope" checked={selected === "ampla"} onChange={() => setSelected("ampla")} /><span><strong>Ampla</strong> Inclui relações confirmadas com outras famílias.</span></label>
      </fieldset>
      <button className="yellow-button" type="button" disabled={!selected || submitting} onClick={() => void submit()}>
        {submitting ? "Ativando..." : "Ativar notificações"}
      </button>
    </section>
  );
}

function formatReason(reason: NotificationReason) {
  return reason.type === "novo_documento"
    ? "Documento novo indexado"
    : `Correlato por ${reason.relation_type} com ${reason.neighbor_family_id}`;
}

function formatDocumentType(value: string) {
  return value.split("_").map((part) => `${part.slice(0, 1).toLocaleUpperCase("pt-BR")}${part.slice(1)}`).join(" ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
