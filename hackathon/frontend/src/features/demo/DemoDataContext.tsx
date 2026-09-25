import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

import { prepareDemoData, type DemoIngestion } from "../../api/ingestions";
import { useSession } from "../auth/SessionContext";

type DemoDataState =
  | { kind: "idle" | "preparing" }
  | { kind: "ready"; ingestion: DemoIngestion }
  | { kind: "error" };

type DemoDataContextValue = DemoDataState & { retry: () => void };

const DemoDataContext = createContext<DemoDataContextValue | null>(null);

export function DemoDataProvider({ children }: PropsWithChildren) {
  const { user, activePersona } = useSession();
  const [state, setState] = useState<DemoDataState>({ kind: "idle" });
  const [attempt, setAttempt] = useState(0);
  const preparation = useRef<Promise<DemoIngestion> | null>(null);

  const retry = useCallback(() => {
    preparation.current = null;
    setAttempt((current) => current + 1);
  }, []);

  useEffect(() => {
    if (!user || !activePersona) {
      setState({ kind: "idle" });
      return;
    }

    let active = true;
    setState({ kind: "preparing" });
    preparation.current ??= prepareDemoData();
    preparation.current
      .then((ingestion) => {
        if (active) setState({ kind: "ready", ingestion });
      })
      .catch(() => {
        preparation.current = null;
        if (active) setState({ kind: "error" });
      });

    return () => {
      active = false;
    };
  }, [activePersona, attempt, user]);

  const value = useMemo<DemoDataContextValue>(() => ({ ...state, retry }), [retry, state]);
  return <DemoDataContext.Provider value={value}>{children}</DemoDataContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDemoData() {
  const context = useContext(DemoDataContext);
  if (!context) throw new Error("useDemoData deve ser usado dentro de DemoDataProvider");
  return context;
}
