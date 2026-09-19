---
concern_id: i6-telemetry
concern: ~/.claude/skills/perspec-me/catalog/concerns/i6-telemetry/README.md
perspective: infrastructure
status: partial
topics:
  - issue-6 — O que dispara uma notificação (novo documento? mudança em processo acompanhado?) e o que ela contém na página inicial e no e-mail?
  - issue-7 — Como a entrega de e-mail via SES lida com frequência e deduplicação?
updated_at: 2026-09-18
---

## Current resolution

_Nota de manutenção (2026-09-18): a resolução da issue-6 afirma ter escrito esta página, mas ela não existia no repositório; o conteúdo da issue-6 abaixo foi reconstruído a partir do comentário de resolução da própria issue, e a issue-7 é o primeiro Topic a gravar esta página._

A telemetria do TB1 observa o **ciclo de vida das notificações**, da geração à abertura, de forma que o critério de aceite do plano ("frequência aplicada e sem duplicação no cenário testado") seja verificável pelos eventos, não por inspeção manual. Todos os eventos são emitidos pelo `backend` (dono da política de notificação — [[i9-integration]]) e persistidos junto ao catálogo (Postgres no Compose, [[i4-storage]]), nunca dependentes de um serviço AWS.

Eventos (issue-6, base; issue-7, complementos):

| Evento | Emitido por | Campos mínimos |
|---|---|---|
| `notification_generated` | backend, ao indexar versão nova | `notification_id`, `user_id`, `document_version_id`, `family_id`, `scope_effective` (estrita/ampla), `reasons[]` (correlatos incluídos e seus tipos/estados), `ingestion_job_id` |
| `notification_suppressed` | backend, no ponto de dedup | `user_id`, `document_version_id`, `reason` ∈ {`duplicate`, `already_notified_by_other_scope`}, `existing_notification_id` |
| `email_digest_generated` | backend, ao fim do job | `email_id`, `user_id`, `ingestion_job_id`, `notification_count` |
| `notification_delivered_home` | backend | `notification_id`, `user_id` |
| `notification_delivered_email` | adapter `Mailer` | `email_id`, `adapter` ∈ {`preview`, `ses`}, `status`, `provider_message_id?`, `error?` (ex.: destinatário não verificado no sandbox) |
| `notification_opened` / `notification_clicked` | backend, ao resolver o link com token | `notification_id`, `email_id?`, `origin` ∈ {`home`, `email`} |

Abertura de e-mail é medida **só pelo clique no link com token** — sem pixel de rastreamento. O adapter de prévia emite `notification_delivered_email` com `adapter: preview`, para que o fluxo completo seja observável no 1º ciclo mesmo sem SES.

## Confirmed facts

- 2026-09-18 (issue-6): gatilho = qualquer documento novo indexado (família nova ou versão nova); escopo por usuário estrita/ampla sem padrão; conteúdo linka direto para trecho/versão; notificação estritamente informativa.
- 2026-09-18 (issue-8 / [[i2-model-serving]]): sem envio real de e-mail no 1º ciclo; único adapter ativo é a prévia na página inicial.
- Plano l.191: aceite do alerta = "frequência aplicada e sem duplicação no cenário testado".

## Decisions

- 2026-09-18 (issue-6): eventos `notification_generated`, `notification_delivered_home`/`_email`, `notification_opened`/`_clicked` existem desde o TB1.
- 2026-09-18 (issue-7): acrescentados `notification_suppressed` (com motivo) e `email_digest_generated`; `notification_delivered_email` carrega `adapter` e `email_id`.
- 2026-09-18 (issue-7): abertura de e-mail medida por clique em link com token; sem pixel.

## Derived requirements and constraints

- Todo evento carrega `user_id` e, quando aplicável, `notification_id`/`email_id`, para que "sem duplicação" seja auditável por consulta: nenhum `(user_id, document_version_id)` com dois `notification_generated`.
- `notification_delivered_email` é emitido pelo adapter (prévia ou SES) através do `DeliveryReport` devolvido por `Mailer.send` — o backend grava o evento, o adapter só reporta ([[i9-integration]]).
- Chamadas reais ao SES (quando existirem) registram destinatário e `MessageId` — exigência de auditoria de custo em [[i11-cost]].
- Eventos persistem no Postgres local; nada de CloudWatch no 1º ciclo.

## Open questions

- (issue-6/7) Telemetria de uso da busca (consultas, cliques em resultados, 👍/👎 de `POST /v1/feedback` da issue-5) ainda não foi tratada por nenhum Topic — esta página cobre só notificações.
- (issue-7) Se a ingestão virar contínua, `email_digest_generated` passa a ser por período, não por job.

## Evidence

- Comentário de resolução da issue #6 (GitHub), seção "Telemetria".
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` l.50, 86, 112, 191.
- `hackathon/scripts/check_aws_capabilities.out` l.317–334 (SES negado; observação sobre sandbox).

## Topic history

- issue-6: definiu os eventos base do ciclo de notificação (gerada, entregue home/e-mail, aberta/clicada) — página não gravada na época; reconstruída aqui.
- issue-7: criou a página; acrescentou `notification_suppressed` e `email_digest_generated`, `adapter`/`email_id` na entrega por e-mail, e abertura por clique com token.
