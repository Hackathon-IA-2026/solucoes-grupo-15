import { createContext, useContext, useMemo, useState, type PropsWithChildren } from "react";

import { mockUser } from "../../mocks/auth";
import type { PersonaId, SessionUser } from "../../types/product";

type SessionState = { user: SessionUser | null; activePersona: PersonaId | null };
type SessionContextValue = SessionState & {
  login: (email: string) => void;
  selectPersona: (persona: PersonaId) => void;
  logout: () => void;
};

const STORAGE_KEY = "capiwatt-lens:mock-session";
const SessionContext = createContext<SessionContextValue | null>(null);

function loadSession(): SessionState {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored) as SessionState;
  } catch {
    return { user: null, activePersona: null };
  }
  return { user: null, activePersona: null };
}

export function SessionProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<SessionState>(loadSession);

  function persist(next: SessionState) {
    setSession(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // A sessão mockada continua em memória quando o storage não está disponível.
    }
  }

  const value = useMemo<SessionContextValue>(() => ({
    ...session,
    login: (email) => persist({ user: { ...mockUser, email }, activePersona: null }),
    selectPersona: (activePersona) => persist({ ...session, activePersona }),
    logout: () => {
      setSession({ user: null, activePersona: null });
      try { window.localStorage.removeItem(STORAGE_KEY); } catch { /* sessão em memória já encerrada */ }
    },
  }), [session]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession deve ser usado dentro de SessionProvider");
  return context;
}
