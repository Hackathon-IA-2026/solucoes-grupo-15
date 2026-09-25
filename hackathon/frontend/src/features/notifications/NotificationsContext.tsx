import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import { runDemoIngestion } from "../../api/ingestions";
import {
  chooseNotificationScope,
  fetchEmailDigests,
  fetchNotifications,
  fetchNotificationScope,
  markNotificationOpened,
  type EmailDigestPreview,
  type NotificationItem,
  type NotificationScope,
} from "../../api/notifications";
import { useSession } from "../auth/SessionContext";
import { useDemoData } from "../demo/DemoDataContext";

type NotificationsState =
  | { kind: "idle" | "loading" }
  | { kind: "scope-required" }
  | {
      kind: "ready";
      scope: NotificationScope;
      notifications: NotificationItem[];
      digests: EmailDigestPreview[];
    }
  | { kind: "error" };

type NotificationsContextValue = NotificationsState & {
  chooseScope: (scope: NotificationScope) => Promise<void>;
  openNotification: (notificationId: number) => Promise<void>;
  retry: () => void;
};

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

export function NotificationsProvider({ children }: PropsWithChildren) {
  const { user } = useSession();
  const demoData = useDemoData();
  const [state, setState] = useState<NotificationsState>({ kind: "idle" });
  const [attempt, setAttempt] = useState(0);

  const loadReadyState = useCallback(async (userId: string, scope: NotificationScope) => {
    const [notifications, digests] = await Promise.all([
      fetchNotifications(userId),
      fetchEmailDigests(userId),
    ]);
    setState({ kind: "ready", scope, notifications, digests });
  }, []);

  useEffect(() => {
    if (!user) {
      setState({ kind: "idle" });
      return;
    }

    let active = true;
    setState((current) => current.kind === "scope-required" ? current : { kind: "loading" });
    fetchNotificationScope(user.id)
      .then(async (scope) => {
        if (!active) return;
        if (scope === null) {
          setState({ kind: "scope-required" });
          return;
        }
        if (demoData.kind !== "ready") return;
        const [notifications, digests] = await Promise.all([
          fetchNotifications(user.id),
          fetchEmailDigests(user.id),
        ]);
        if (active) setState({ kind: "ready", scope, notifications, digests });
      })
      .catch(() => {
        if (active) setState({ kind: "error" });
      });

    return () => {
      active = false;
    };
  }, [attempt, demoData.kind, user]);

  const chooseScope = useCallback(async (scope: NotificationScope) => {
    if (!user) return;
    setState({ kind: "loading" });
    try {
      await chooseNotificationScope(user.id, scope);
      await runDemoIngestion();
      await loadReadyState(user.id, scope);
    } catch (error) {
      setState({ kind: "error" });
      throw error;
    }
  }, [loadReadyState, user]);

  const openNotification = useCallback(async (notificationId: number) => {
    await markNotificationOpened(notificationId);
    setState((current) => current.kind === "ready"
      ? {
          ...current,
          notifications: current.notifications.map((notification) =>
            notification.id === notificationId ? { ...notification, opened: true } : notification,
          ),
        }
      : current);
  }, []);

  const retry = useCallback(() => setAttempt((current) => current + 1), []);
  const value = useMemo<NotificationsContextValue>(
    () => ({ ...state, chooseScope, openNotification, retry }),
    [chooseScope, openNotification, retry, state],
  );

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useNotifications() {
  const context = useContext(NotificationsContext);
  if (!context) throw new Error("useNotifications deve ser usado dentro de NotificationsProvider");
  return context;
}
