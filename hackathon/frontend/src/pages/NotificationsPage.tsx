import { useEffect, useState } from "react";
import { ArrowUpRight, Bell, Inbox, Mail, UserRound } from "lucide-react";
import { Link } from "react-router-dom";

import {
  chooseNotificationScope,
  DEMO_USERS,
  fetchEmailDigests,
  fetchNotifications,
  fetchNotificationScope,
  loadDemoUser,
  markNotificationOpened,
  saveDemoUser,
  type DemoUser,
  type EmailDigestPreview,
  type NotificationItem,
  type NotificationReason,
  type NotificationScope,
} from "../api/notifications";
import { DemoBanner } from "../components/DemoBanner";

/**
 * Página de notificações (TB1 Ticket 8, issue #24) - rota
 * "/notificacoes", separada da busca ("/", que continua sendo a tela
 * principal, decisão fechada no Ticket 3).
 *
 * Um seletor de usuário demo (`DEMO_USERS`, api/notifications.ts)
 * troca de quem está "vendo" a central de notificações - não é login,
 * ver o comentário no módulo da API. Enquanto o usuário selecionado
 * não tiver escolhido `notification_scope`, só o seletor obrigatório
 * de escopo aparece (sem opção pré-selecionada, decisão fechada em
 * u3-frequency.md) - nenhuma notificação é mostrada antes disso.
 * Depois de escolhido: lista as notificações (linkando para
 * `/documents/{family_id}`, registrando abertura ao clicar) e, numa
 * seção separada, a prévia dos digests de e-mail.
 */

type ScopeState =
  | { kind: "loading" }
  | { kind: "unset" }
  | { kind: "set"; scope: NotificationScope }
  | { kind: "error" };

type ListState<T> = { kind: "loading" } | { kind: "result"; items: T[] } | { kind: "error" };

export function NotificationsPage() {
  const [user, setUser] = useState<DemoUser>(() => loadDemoUser());
  const [scopeState, setScopeState] = useState<ScopeState>({ kind: "loading" });
  const [notificationsState, setNotificationsState] = useState<ListState<NotificationItem>>({
    kind: "loading",
  });
  const [digestsState, setDigestsState] = useState<ListState<EmailDigestPreview>>({
    kind: "loading",
  });

  useEffect(() => {
    saveDemoUser(user);
  }, [user]);

  useEffect(() => {
    let cancelled = false;
    setScopeState({ kind: "loading" });
    fetchNotificationScope(user)
      .then((scope) => {
        if (!cancelled) {
          setScopeState(scope === null ? { kind: "unset" } : { kind: "set", scope });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setScopeState({ kind: "error" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  useEffect(() => {
    if (scopeState.kind !== "set") {
      return;
    }
    setNotificationsState({ kind: "loading" });
    fetchNotifications(user)
      .then((items) => setNotificationsState({ kind: "result", items }))
      .catch(() => setNotificationsState({ kind: "error" }));

    setDigestsState({ kind: "loading" });
    fetchEmailDigests(user)
      .then((items) => setDigestsState({ kind: "result", items }))
      .catch(() => setDigestsState({ kind: "error" }));
  }, [user, scopeState.kind]);

  async function handleChooseScope(scope: NotificationScope): Promise<void> {
    await chooseNotificationScope(user, scope);
    setScopeState({ kind: "set", scope });
  }

  function handleOpenNotification(notificationId: number) {
    markNotificationOpened(notificationId).catch(() => {
      // abertura é só telemetria - não deve bloquear a navegação do usuário.
    });
  }

  return (
    <div className="page notifications-page">
      <DemoBanner />

      <header className="search-intro">
        <p className="eyebrow">
          <Bell size={15} /> Notificações
        </p>
        <h1>Central de notificações</h1>
        <p className="intro-copy">
          Documentos novos indexados no corpus geram uma notificação por usuário com escopo
          escolhido, mostrada aqui imediatamente, e um digest de e-mail por ingestão (prévia,
          sem envio real).
        </p>
      </header>

      <UserSelector user={user} onChange={setUser} />

      <section aria-label="conteúdo de notificações">
        {scopeState.kind === "loading" && (
          <div className="loading-state">
            <span className="loading-spinner" aria-hidden="true" /> Carregando...
          </div>
        )}
        {scopeState.kind === "error" && (
          <div className="empty-state error-state">
            <h2>Não foi possível carregar sua preferência de notificação.</h2>
            <p>Tente novamente em alguns instantes.</p>
          </div>
        )}
        {scopeState.kind === "unset" && <ScopePicker onChoose={handleChooseScope} />}
        {scopeState.kind === "set" && (
          <NotificationsContent
            scope={scopeState.scope}
            notificationsState={notificationsState}
            digestsState={digestsState}
            onOpenNotification={handleOpenNotification}
          />
        )}
      </section>
    </div>
  );
}

function UserSelector({
  user,
  onChange,
}: {
  user: DemoUser;
  onChange: (user: DemoUser) => void;
}) {
  return (
    <div className="demo-user-picker">
      <label htmlFor="demo-user-select">
        <UserRound size={14} aria-hidden="true" /> Usuário demo (seleção de demonstração, não é
        login)
      </label>
      <select
        id="demo-user-select"
        value={user}
        onChange={(event) => onChange(event.target.value as DemoUser)}
      >
        {DEMO_USERS.map((demoUser) => (
          <option key={demoUser} value={demoUser}>
            {demoUser}
          </option>
        ))}
      </select>
    </div>
  );
}

function ScopePicker({
  onChoose,
}: {
  onChoose: (scope: NotificationScope) => Promise<void>;
}) {
  const [selected, setSelected] = useState<NotificationScope | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(false);

  async function handleConfirm() {
    if (!selected) {
      return;
    }
    setSubmitting(true);
    setError(false);
    try {
      await onChoose(selected);
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="empty-state scope-picker">
      <h2>Escolha o escopo das suas notificações</h2>
      <p>
        Antes de ver notificações, escolha um dos dois escopos abaixo. Não há opção padrão — a
        escolha é obrigatória para cada usuário.
      </p>
      <fieldset>
        <legend className="sr-only">Escopo de notificação</legend>
        <label className="scope-option">
          <input
            type="radio"
            name="notification-scope"
            value="estrita"
            checked={selected === "estrita"}
            onChange={() => setSelected("estrita")}
          />
          <span>
            <strong>Estrita</strong> — só o processo/família do documento novo.
          </span>
        </label>
        <label className="scope-option">
          <input
            type="radio"
            name="notification-scope"
            value="ampla"
            checked={selected === "ampla"}
            onChange={() => setSelected("ampla")}
          />
          <span>
            <strong>Ampla</strong> — inclui correlatos (famílias/processos ligados por relação
            confirmada).
          </span>
        </label>
      </fieldset>
      <button
        className="primary-button"
        type="button"
        disabled={!selected || submitting}
        onClick={handleConfirm}
      >
        Confirmar escopo
      </button>
      {error && (
        <p className="feedback-message error">
          Não foi possível salvar sua escolha. Tente novamente.
        </p>
      )}
    </div>
  );
}

function NotificationsContent({
  scope,
  notificationsState,
  digestsState,
  onOpenNotification,
}: {
  scope: NotificationScope;
  notificationsState: ListState<NotificationItem>;
  digestsState: ListState<EmailDigestPreview>;
  onOpenNotification: (notificationId: number) => void;
}) {
  return (
    <>
      <p className="panel-status">
        Escopo atual de <strong>{scope}</strong>. Para trocar, escolha novamente na tela de
        configuração (evolução futura).
      </p>

      <section className="results-section" aria-label="lista de notificações">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              <Inbox size={15} /> Página inicial
            </p>
            <h2>Notificações</h2>
          </div>
          {notificationsState.kind === "result" && (
            <span>{notificationsState.items.length} notificação(ões)</span>
          )}
        </div>
        {notificationsState.kind === "loading" && (
          <div className="loading-state">
            <span className="loading-spinner" aria-hidden="true" /> Carregando...
          </div>
        )}
        {notificationsState.kind === "error" && (
          <div className="empty-state error-state">
            <h2>Não foi possível carregar as notificações.</h2>
          </div>
        )}
        {notificationsState.kind === "result" && notificationsState.items.length === 0 && (
          <p className="empty-state">
            Nenhuma notificação ainda. Uma nova ingestão do corpus (POST /v1/ingestions) gera
            notificações para este usuário.
          </p>
        )}
        {notificationsState.kind === "result" && notificationsState.items.length > 0 && (
          <ul className="result-list notification-list">
            {notificationsState.items.map((item) => (
              <NotificationCard
                key={item.id}
                notification={item}
                onOpen={() => onOpenNotification(item.id)}
              />
            ))}
          </ul>
        )}
      </section>

      <section className="results-section" aria-label="prévias de e-mail">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              <Mail size={15} /> Prévia — sem envio real
            </p>
            <h2>Digest de e-mail</h2>
          </div>
          {digestsState.kind === "result" && <span>{digestsState.items.length} digest(s)</span>}
        </div>
        {digestsState.kind === "loading" && (
          <div className="loading-state">
            <span className="loading-spinner" aria-hidden="true" /> Carregando...
          </div>
        )}
        {digestsState.kind === "error" && (
          <div className="empty-state error-state">
            <h2>Não foi possível carregar as prévias de e-mail.</h2>
          </div>
        )}
        {digestsState.kind === "result" && digestsState.items.length === 0 && (
          <p className="empty-state">Nenhum digest de e-mail gerado ainda para este usuário.</p>
        )}
        {digestsState.kind === "result" && digestsState.items.length > 0 && (
          <ul className="email-digest-list">
            {digestsState.items.map((digest) => (
              <li key={digest.email_id} className="email-digest-item">
                <p className="result-meta">{digest.email_id}</p>
                <pre>{digest.rendered_body}</pre>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

function NotificationCard({
  notification,
  onOpen,
}: {
  notification: NotificationItem;
  onOpen: () => void;
}) {
  return (
    <li className="result-card notification-card">
      <div className="result-main">
        <div className="result-label-row">
          <span className="document-type">{notification.document_type ?? "documento"}</span>
          <span className="version-pill">{notification.scope_effective}</span>
        </div>
        <h3>{notification.document_id ?? notification.document_version_id}</h3>
        <ReasonsList reasons={notification.reasons} />
        <div className="result-actions">
          <Link
            className="detail-link"
            to={`/documents/${encodeURIComponent(notification.family_id)}`}
            onClick={onOpen}
          >
            Ver documento <ArrowUpRight size={14} aria-hidden="true" />
          </Link>
        </div>
      </div>
    </li>
  );
}

function ReasonsList({ reasons }: { reasons: NotificationReason[] }) {
  return (
    <ul className="notification-reasons">
      {reasons.map((reason, index) => (
        <li key={index}>{formatReason(reason)}</li>
      ))}
    </ul>
  );
}

function formatReason(reason: NotificationReason): string {
  if (reason.type === "novo_documento") {
    return "Documento novo indexado";
  }
  return `Correlato (${reason.relation_type}) com ${reason.neighbor_family_id}`;
}

export default NotificationsPage;
