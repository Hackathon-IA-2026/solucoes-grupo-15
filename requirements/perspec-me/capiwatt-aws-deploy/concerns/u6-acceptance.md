---
concern_id: u6-acceptance
concern: ~/.claude/skills/perspec-me/catalog/concerns/u6-acceptance/README.md
perspective: user-experience
status: resolved
topics:
  - topic-frontend-hosting
  - topic-cognito-auth
updated_at: 2026-09-26
---

## Current resolution

A experiência da Carolina na AWS é a mesma do local: mesmas rotas (links diretos funcionam, pelo fallback SPA), mesma origem para a API e HTTPS pelo CloudFront. O login via Cognito existe só na AWS; localmente, sem Cognito no `config.json`, o app segue no modo demo sem login. Na AWS, a Carolina e os avaliadores entram pela tela de login atual do app, digitando e-mail ou usuário (`carolina@capiwatt.demo` ou `carolina`), com uma senha de demonstração fixa e compartilhada. Não há troca de senha no primeiro acesso nem auto-cadastro.

## Confirmed facts

- O frontend usa `BrowserRouter` (`src/App.tsx`) e chamadas relativas a `/v1`.

## Decisions

- 2026-09-26 (Eduardo, topic-cognito-auth): login dentro do app via SRP (Amplify Auth), com a identidade visual do app, sem Hosted UI e sem auto-cadastro; com Cognito ativo o seletor de usuário demo some.

- 2026-09-26 (Eduardo, topic-frontend-hosting): `config.json` em runtime; a ausência de Cognito liga o modo demo sem login.

- 2026-09-26 (Eduardo, topic-cognito-auth): contas padrão `carolina`, `equipe` (os perfis demo que já existem) e `admin`; contas por pessoa do time são opcionais, acrescentadas pela lista no `.env`.
- 2026-09-26 (Eduardo, topic-cognito-auth): senha fixa e permanente, sem `NEW_PASSWORD_REQUIRED`: uma `DEMO_PASSWORD` compartilhada pelas contas de demo (entregue aos avaliadores) e uma `ADMIN_PASSWORD` separada, só do time.
- 2026-09-26 (Eduardo, topic-cognito-auth): login por e-mail ou usuário (`signInAliases: { username, email }`), com e-mail fictício `<user_id>@capiwatt.demo` marcado como verificado pelo script.

## Derived requirements and constraints

- A `LoginPage` atual (campo "seu@email.com ou usuário", valor inicial `carolina@capiwatt.demo`, aviso "Sem cadastro self-service") serve sem mudança de texto; só troca o `login` mock pela chamada SRP do Amplify.
- Uma senha compartilhada não pode ser trocada pela UI: o app não expõe "alterar senha", para um avaliador não quebrar a demo dos seguintes.
- Contas novas (por exemplo, por pessoa do time) começam sem escopo de notificação; a escolha de escopo já existente no app cobre isso.
- Um deep link (por exemplo, uma notificação apontando para um documento) precisa abrir direto na AWS: coberto pela CloudFront Function.

## Open questions


## Evidence

- `hackathon/frontend/src/App.tsx:22`, `hackathon/frontend/package.json`.
- `hackathon/frontend/src/pages/LoginPage.tsx:11,36,43`: login já prevê e-mail ou usuário e declara acesso provisionado pela equipe.
- `hackathon/frontend/src/api/notifications.ts:18`: `DEMO_USERS = ["carolina", "equipe"]`.

## Topic history

- topic-cognito-auth: login SRP no app, sem auto-cadastro; contas `carolina`/`equipe`/`admin`, senha fixa compartilhada e login por e-mail ou usuário.
- topic-frontend-hosting: paridade local/AWS e modo demo sem login.
