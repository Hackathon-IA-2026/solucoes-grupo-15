---
concern_id: i6-telemetry
concern: ~/.claude/skills/perspec-me/catalog/concerns/i6-telemetry/README.md
perspective: infrastructure
status: resolved
topics:
  - topic-cognito-auth
  - topic-aws-observability
updated_at: 2026-09-27
---

## Current resolution

Os eventos de notificação (Map irmão) continuam gravando `user_id`; na AWS com `AUTH_MODE=cognito` esse valor vem de uma identidade autenticada (claim `username`), sem mudança de schema.

Na AWS (topic-aws-observability), backend e `ai` enviam logs pelo driver `awslogs` para `/capiwatt/backend` e `/capiwatt/ai`, com retenção de 3 dias. O backend escreve uma linha JSON por requisição com `user_id`, `trace_id` (`X-Amzn-Trace-Id` do ALB) e, nas buscas, `search_request_id`. Esse id liga o log à `SearchExecution` e ao replay. O código do `ai` não muda. A borda fica só com as métricas gratuitas do CloudWatch. O limite de atribuição da senha de demo compartilhada fica aceito.

## Confirmed facts

- O backend aceita qualquer string como `user_id` e só gera notificação depois que o usuário escolhe o escopo (`hackathon/backend/app/models.py:146-152`).

## Decisions

- 2026-09-26 (Eduardo, topic-cognito-auth): username do Cognito = `user_id` existente; schema de eventos inalterado.

- 2026-09-26 (Eduardo, topic-cognito-auth): na AWS, os `user_id` possíveis nos eventos são exatamente as contas do script (`carolina`, `equipe`, `admin` e as opcionais do `.env`); como a senha de demo é compartilhada, `carolina` nos eventos significa "alguém com a senha de demo", não uma pessoa identificada.

- 2026-09-27 (Eduardo por delegação, topic-aws-observability): um grupo do CloudWatch Logs por serviço (`/capiwatt/backend`, `/capiwatt/ai`), driver `awslogs`, retenção de 3 dias, `RemovalPolicy.DESTROY`.
- 2026-09-27 (Eduardo por delegação, topic-aws-observability): sem access logs do ALB, logs padrão do CloudFront, Container Insights, X-Ray, alarmes ou dashboards. A borda fica com as métricas gratuitas do CloudWatch.
- 2026-09-27 (Eduardo por delegação, topic-aws-observability): middleware no backend escreve no stdout uma linha JSON por requisição (`ts`, `method`, `path`, `status`, `duration_ms`, `user_id`, `trace_id` = `X-Amzn-Trace-Id` ou `-`, `search_request_id` em `/v1/search`), sem corpo, consulta, token ou senha. O formato é o mesmo no Compose e o código do `ai` não muda.
- 2026-09-27 (Eduardo por delegação, topic-aws-observability): sem contas por avaliador; atribuição individual, quando necessária, pelas contas opcionais de `COGNITO_USERS`.

## Derived requirements and constraints

- Métricas de uso na AWS não podem atribuir eventos de `carolina`/`equipe` a um avaliador específico.
- Nenhum header ou campo novo no contrato frontend ↔ backend: `trace_id` é só lido do header posto pelo ALB.
- A evidência de avaliação do M4 fica no artefato da comparação e em `SearchExecution`, nunca nos logs (retenção de 3 dias).
- O README de `hackathon/infra/` documenta duas consultas do Logs Insights: busca por `search_request_id` e erros 5xx por `path`.

## Open questions

- Nenhuma para a Destination atual.

## Evidence

- `hackathon/backend/app/models.py:146-152`.
- Sem configuração de `logging` no backend nem no `ai`; só o access log do uvicorn (busca no código em 2026-09-27).
- `request_id` da busca: `hackathon/backend/app/routes/search.py:221` (uuid4), persistido em `SearchExecution` (`models.py:282`); replay em `routes/search.py:355` e `app/replay.py`.
- [Sondagem de capacidades AWS](../evidence/2026-09-26-aws-capability-probe.md): CloudWatch Logs liberado ao participante.

## Topic history

- topic-cognito-auth: origem autenticada do `user_id` nos eventos; conjunto fechado de contas e limite de atribuição pela senha compartilhada.
- topic-aws-observability: grupos do CloudWatch por serviço com retenção de 3 dias, log JSON por requisição no backend com `trace_id`/`search_request_id`, borda só com métricas; limite de atribuição aceito.
