import { useEffect, useState } from "react";

import { fetchBackendHealth, type BackendHealth } from "./api/health";

type HealthStatus =
  | { kind: "loading" }
  | { kind: "ok"; health: BackendHealth }
  | { kind: "error" };

/**
 * Tela unica deste ticket: mostra o resultado do health check cruzado
 * (backend -> ai) consumindo so a API /v1/health do backend.
 */
export function App() {
  const [status, setStatus] = useState<HealthStatus>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchBackendHealth()
      .then((health) => {
        if (!cancelled) {
          setStatus({ kind: "ok", health });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus({ kind: "error" });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main>
      <h1>CapiWatt Lens</h1>
      <section aria-label="status do sistema">
        {status.kind === "loading" && <p>Verificando status...</p>}
        {status.kind === "ok" && (
          <p>
            backend: {status.health.backend}, ai: {status.health.ai}
          </p>
        )}
        {status.kind === "error" && <p>Não foi possível consultar o backend.</p>}
      </section>
    </main>
  );
}

export default App;
