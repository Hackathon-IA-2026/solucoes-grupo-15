import { useEffect, useState } from "react";

import { fetchBackendHealth, type BackendHealth } from "../api/health";

type HealthStatus =
  | { kind: "loading" }
  | { kind: "ok"; health: BackendHealth }
  | { kind: "error" };

/**
 * Indicador discreto de rodape do health check cruzado (backend -> ai).
 *
 * Ate o Ticket 2, o health check era a tela principal (ver historico de
 * src/App.tsx); a partir do Ticket 3 (issue #19) a busca vira a tela
 * principal e este componente passa a viver so no rodape.
 */
export function HealthBadge() {
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
    <p aria-label="status do sistema">
      {status.kind === "loading" && "Verificando status..."}
      {status.kind === "ok" && `backend: ${status.health.backend}, ai: ${status.health.ai}`}
      {status.kind === "error" && "Não foi possível consultar o backend."}
    </p>
  );
}

export default HealthBadge;
