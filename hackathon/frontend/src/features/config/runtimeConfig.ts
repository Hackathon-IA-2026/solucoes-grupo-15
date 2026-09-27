/**
 * Configuração em runtime do frontend (issue #102, spec #101).
 *
 * Na AWS, o deploy publica `/config.json` junto do bundle estático com os
 * dados do User Pool do Cognito, no formato
 * `{ region, userPoolId, userPoolClientId }`. Assim o mesmo build serve
 * qualquer ambiente, sem rebuild por conta. No Compose/Vite o arquivo não
 * existe (404, ou o `index.html` do fallback de SPA): o app segue no modo
 * demo atual, com o seletor `carolina`/`equipe`.
 */

export type CognitoConfig = {
  region: string;
  userPoolId: string;
  userPoolClientId: string;
};

/** `cognito: null` significa modo demo (sem login real). */
export type RuntimeConfig = {
  cognito: CognitoConfig | null;
};

export const DEMO_RUNTIME_CONFIG: RuntimeConfig = { cognito: null };

/**
 * Busca e interpreta `/config.json`. Nunca lança: 404, falha de rede,
 * corpo que não é JSON ou JSON sem os três campos do Cognito caem todos
 * no modo demo, sem erro visível.
 */
export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  try {
    const response = await fetch("/config.json");
    if (!response.ok) return DEMO_RUNTIME_CONFIG;
    return { cognito: parseCognitoConfig(await response.json()) };
  } catch {
    return DEMO_RUNTIME_CONFIG;
  }
}

function parseCognitoConfig(body: unknown): CognitoConfig | null {
  if (!body || typeof body !== "object") return null;
  const { region, userPoolId, userPoolClientId } = body as Record<string, unknown>;
  if (!isFilled(region) || !isFilled(userPoolId) || !isFilled(userPoolClientId)) return null;
  return { region, userPoolId, userPoolClientId };
}

function isFilled(value: unknown): value is string {
  return typeof value === "string" && value.trim() !== "";
}
