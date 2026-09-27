---
concern_id: i6-telemetry
concern: ~/.claude/skills/perspec-me/catalog/concerns/i6-telemetry/README.md
perspective: infrastructure
status: partial
topics:
  - topic-cognito-auth
updated_at: 2026-09-26
---

## Current resolution

Os eventos de notificação (Map irmão) continuam gravando `user_id`; na AWS com `AUTH_MODE=cognito` esse valor vem de uma identidade autenticada (claim `username`), sem mudança de schema. A observabilidade de infraestrutura na AWS (CloudWatch) segue no Fog.

## Confirmed facts

- O backend aceita qualquer string como `user_id` e só gera notificação depois que o usuário escolhe o escopo (`hackathon/backend/app/models.py:146-152`).

## Decisions

- 2026-09-26 (Eduardo, topic-cognito-auth): username do Cognito = `user_id` existente; schema de eventos inalterado.

- 2026-09-26 (Eduardo, topic-cognito-auth): na AWS, os `user_id` possíveis nos eventos são exatamente as contas do script (`carolina`, `equipe`, `admin` e as opcionais do `.env`); como a senha de demo é compartilhada, `carolina` nos eventos significa "alguém com a senha de demo", não uma pessoa identificada.

## Derived requirements and constraints

- Métricas de uso na AWS não podem atribuir eventos de `carolina`/`equipe` a um avaliador específico.

## Open questions

- Logs e métricas na AWS (Fog "Observabilidade na AWS").

## Evidence

- `hackathon/backend/app/models.py:146-152`.

## Topic history

- topic-cognito-auth: origem autenticada do `user_id` nos eventos; conjunto fechado de contas e limite de atribuição pela senha compartilhada.
