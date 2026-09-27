/**
 * Ponto único do cliente HTTP do frontend para a API `/v1/*` do backend
 * (issue #102, prefactor da implantação AWS da spec #101).
 *
 * Toda função de `src/api/` chama `apiFetch` em vez de `fetch`. Os
 * caminhos continuam relativos (o proxy do Vite no Compose, o CloudFront
 * na AWS) e cada função segue aplicando `encodeURIComponent` nos ids.
 *
 * `setRequestHeadersProvider` é a seam para o login Cognito: o provedor
 * é consultado a cada requisição (o token pode ter sido renovado) e seus
 * headers são somados aos da chamada. Sem provedor, que é o modo demo,
 * `fetch` recebe exatamente os argumentos originais.
 */

export type RequestHeadersProvider = () =>
  | Record<string, string>
  | undefined
  | Promise<Record<string, string> | undefined>;

let headersProvider: RequestHeadersProvider | null = null;

export function setRequestHeadersProvider(provider: RequestHeadersProvider | null): void {
  headersProvider = provider;
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const extraHeaders = headersProvider ? await headersProvider() : undefined;
  if (!extraHeaders || Object.keys(extraHeaders).length === 0) {
    return init ? fetch(path, init) : fetch(path);
  }
  return fetch(path, {
    ...init,
    headers: { ...headersToRecord(init?.headers), ...extraHeaders },
  });
}

function headersToRecord(headers: HeadersInit | undefined): Record<string, string> {
  if (!headers) return {};
  if (headers instanceof Headers) return Object.fromEntries(headers.entries());
  if (Array.isArray(headers)) return Object.fromEntries(headers);
  return { ...headers };
}
