/**
 * Cliente do frontend para notificações + prévia de e-mail (TB1 Ticket
 * 8, issue #24).
 *
 * Chama só GET/PUT /v1/users/{userId}/notification-scope,
 * GET /v1/users/{userId}/notifications, GET /v1/users/{userId}/email-digests
 * e POST /v1/notifications/{id}/opened no backend.
 *
 * **Usuário demo, não login**: este scaffold não tem autenticação (fora
 * de escopo de toda a spec #16). `DEMO_USERS` é um conjunto fixo e
 * pequeno de ids hardcoded para demonstrar "cada usuário escolhe seu
 * escopo" sem inventar um sistema de login real - `userId` é só uma
 * string enviada em cada chamada, sem senha/sessão/token. O usuário
 * escolhido é persistido em `localStorage` só por conveniência de demo
 * (nunca em cookie de sessão, nunca com credencial).
 */

export const DEMO_USERS = ["carolina", "equipe"] as const;
export type DemoUser = (typeof DEMO_USERS)[number];

export type NotificationScope = "estrita" | "ampla";

export type NotificationReason =
  | { type: "novo_documento" }
  | {
      type: "correlato";
      relation_type: string;
      neighbor_family_id: string;
      neighbor_kind: string;
    };

export type NotificationItem = {
  id: number;
  user_id: string;
  document_version_id: string;
  family_id: string;
  document_type: string | null;
  document_id: string | null;
  scope_effective: NotificationScope;
  reasons: NotificationReason[];
  ingestion_job_id: string;
  created_at: string;
};

export type EmailDigestPreview = {
  email_id: string;
  user_id: string;
  ingestion_job_id: string;
  notification_ids: number[];
  rendered_body: string;
  created_at: string;
};

const DEMO_USER_STORAGE_KEY = "capiwatt-lens:notifications-demo-user";

/**
 * Lê o usuário demo escolhido anteriormente. Nunca lança - qualquer
 * falha de acesso ao `localStorage` (ex. navegação privada) cai para o
 * primeiro usuário demo.
 */
export function loadDemoUser(): DemoUser {
  try {
    const stored = window.localStorage.getItem(DEMO_USER_STORAGE_KEY);
    if (stored && (DEMO_USERS as readonly string[]).includes(stored)) {
      return stored as DemoUser;
    }
  } catch {
    // conveniência de demo só - falha silenciosa cai para o padrão.
  }
  return DEMO_USERS[0];
}

export function saveDemoUser(user: DemoUser): void {
  try {
    window.localStorage.setItem(DEMO_USER_STORAGE_KEY, user);
  } catch {
    // conveniência de demo só - falha silenciosa não impede a troca de usuário.
  }
}

export async function fetchNotificationScope(userId: string): Promise<NotificationScope | null> {
  const response = await fetch(`/v1/users/${encodeURIComponent(userId)}/notification-scope`);
  if (!response.ok) {
    throw new Error(`Consulta de escopo falhou com status ${response.status}`);
  }
  const body = (await response.json()) as { scope: NotificationScope | null };
  return body.scope;
}

export async function chooseNotificationScope(
  userId: string,
  scope: NotificationScope,
): Promise<void> {
  const response = await fetch(`/v1/users/${encodeURIComponent(userId)}/notification-scope`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scope }),
  });
  if (!response.ok) {
    throw new Error(`Definição de escopo falhou com status ${response.status}`);
  }
}

export async function fetchNotifications(userId: string): Promise<NotificationItem[]> {
  const response = await fetch(`/v1/users/${encodeURIComponent(userId)}/notifications`);
  if (!response.ok) {
    throw new Error(`Consulta de notificações falhou com status ${response.status}`);
  }
  return (await response.json()) as NotificationItem[];
}

export async function fetchEmailDigests(userId: string): Promise<EmailDigestPreview[]> {
  const response = await fetch(`/v1/users/${encodeURIComponent(userId)}/email-digests`);
  if (!response.ok) {
    throw new Error(`Consulta de prévias de e-mail falhou com status ${response.status}`);
  }
  return (await response.json()) as EmailDigestPreview[];
}

export async function markNotificationOpened(notificationId: number): Promise<void> {
  const response = await fetch(`/v1/notifications/${notificationId}/opened`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Registro de abertura falhou com status ${response.status}`);
  }
}
