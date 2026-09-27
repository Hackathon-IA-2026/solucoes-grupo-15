---
question: Como o Cognito autentica a usuária no frontend (Hosted UI vs. login no app via SRP) e como o backend passa a derivar user_id do token sem quebrar o modo demo local sem credenciais?
status: resolved
blocked_by:
  - topic-frontend-hosting
claimed_by: s-2026-09-26-aws-arch
concerns:
  - i9-integration
  - u6-acceptance
  - i6-telemetry
created_at: 2026-09-26
resolved_at: 2026-09-26
---

Issue: https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/91 (sub-issue de #89)

## Notes

Reabre deliberadamente o "Out of Scope: Autenticação e autorização" da #75 (user_id fixo de demo) — apenas para o ambiente AWS.

Decisões parciais (Eduardo, 2026-09-26, "aceito as sugestões"): login no app via SRP (Amplify Auth), sem Hosted UI; sem auto-cadastro, contas por script (`AdminCreateUser`) com username = `user_id`; grupo `admin`; backend `AUTH_MODE=none|cognito` (padrão none) validando access token (JWKS, client_id, token_use, exp) em `/v1/*` exceto `/v1/health`; `user_id` = claim `username`; caminho `/v1/users/{user_id}` precisa casar com o token (senão 403); `/v1/ingestions` e `/v1/demo/reset` só para o grupo `admin`; `seed.sh` usa app client de operação com `admin-initiate-auth`; frontend esconde o seletor demo quando há Cognito; tokens no localStorage aceitos dentro da postura de economia. Pendente: lista de contas e política de senha inicial.

Pendências fechadas (Eduardo, 2026-09-26, "concordo com as sugestões"): contas padrão `carolina`, `equipe` e `admin` (este último só no grupo `admin`), com contas por pessoa do time opcionais via `COGNITO_USERS`/`COGNITO_ADMIN_USERS` no `.env`. Senhas fixas e permanentes (`admin-create-user --message-action SUPPRESS` + `admin-set-user-password --permanent`), com uma `DEMO_PASSWORD` compartilhada pelas contas de demo e uma `ADMIN_PASSWORD` separada; o script é idempotente. O login aceita e-mail ou usuário (`signInAliases`), com o e-mail fictício `<user_id>@capiwatt.demo` verificado pelo script, então a `LoginPage` atual serve sem mudança de texto. Política de senha padrão do Cognito.

## Síntese

Decidido: login SRP no app (sem Hosted UI, sem auto-cadastro), backend `AUTH_MODE=none|cognito` com `user_id` = `username` do token, autorização por caminho e pelo grupo `admin`, contas provisionadas por script a partir do `.env`, senhas fixas e login por e-mail ou usuário. O modo demo local sem credenciais continua o padrão. Concerns tocados: [I9](../concerns/i9-integration.md) `resolved`, [U6](../concerns/u6-acceptance.md) `resolved`, [I6](../concerns/i6-telemetry.md) `partial` (observabilidade AWS segue no Fog). Contrato atualizado: [frontend ↔ backend](../../../contracts/frontend-backend.md).
