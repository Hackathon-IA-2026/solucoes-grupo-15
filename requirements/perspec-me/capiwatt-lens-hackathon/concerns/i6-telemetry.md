---
concern_id: i6-telemetry
concern: ~/.claude/skills/perspec-me/catalog/concerns/i6-telemetry/README.md
perspective: infrastructure
status: partial
topics:
  - issue-6 — O que dispara uma notificação (novo documento? mudança em processo acompanhado?) e o que ela contém na página inicial e no e-mail?
  - issue-7 — Como a entrega de e-mail via SES lida com frequência e deduplicação?
updated_at: 2026-09-20
---

## Current resolution

**Autoridade de disponibilidade (Eduardo, 2026-09-20):** [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md) prevalece sobre hipóteses do plano e diagnósticos anteriores quanto a serviços, regiões e permissões. Diagnósticos datados permanecem evidência histórica; disponibilidade não equivale à validação funcional do fluxo da aplicação.

**Revisão da issue-7 (2026-09-20, aceita por Eduardo):** manter eventos em Postgres local. `notification_delivered_email` com `adapter: preview` comprova geração da prévia, não entrega em caixa postal; a interface deve preservar essa distinção. CloudWatch e demais serviços de observabilidade estão disponíveis conforme o documento, mas não foram selecionados para o primeiro ciclo.

### Base da issue-6

O job de ingestão já emite os eventos de origem (documento indexado, aresta criada — [[d14-data-operations-modeling]]) que alimentam o disparo de notificação. Além desses, a própria notificação emite três eventos (decisão de Eduardo, 2026-09-18):

- `notification_generated` — documento/família gatilho, escopo aplicado (`estrita`/`ampla`) e lista de correlatos incluídos (quando ampla).
- `notification_delivered_home` / `notification_delivered_email` — um evento por canal de entrega.
- `notification_opened` / `notification_clicked` — interação do usuário, com o canal de origem.

Essa base permite observar o ciclo de vida das notificações e sustenta os complementos de deduplicação e frequência da issue-7.

### Complementos da issue-7

A telemetria do TB1 observa o **ciclo de vida das notificações**, da geração à abertura, de forma que o critério de aceite do plano ("frequência aplicada e sem duplicação no cenário testado") seja verificável pelos eventos, não por inspeção manual. O `backend`, dono da política de notificação ([[i9-integration]]), registra os eventos junto ao catálogo (Postgres no Compose, [[i4-storage]]), sem depender de um serviço AWS. Na entrega de e-mail, o adapter `Mailer` reporta o resultado e o backend grava o evento.

Eventos (issue-6, base; issue-7, complementos):

| Evento | Registrado por | Campos mínimos |
|---|---|---|
| `notification_generated` | backend, ao indexar versão nova | `notification_id`, `user_id`, `document_version_id`, `family_id`, `scope_effective` (estrita/ampla), `reasons[]` (família gatilho e, no escopo ampla, correlatos incluídos, com seus tipos/estados — mesmo vocabulário de [[i9-integration]]), `ingestion_job_id` |
| `notification_suppressed` | backend, no ponto de dedup | `user_id`, `document_version_id`, `reason` ∈ {`duplicate`, `already_notified_by_other_scope`}, `existing_notification_id` |
| `email_digest_generated` | backend, ao fim do job | `email_id`, `user_id`, `ingestion_job_id`, `notification_count` |
| `notification_delivered_home` | backend | `notification_id`, `user_id` |
| `notification_delivered_email` | backend, a partir do `DeliveryReport` do adapter `Mailer` | `email_id`, `adapter` ∈ {`preview`, `ses`}, `status`, `provider_message_id?`, `error?` (ex.: destinatário não verificado no sandbox) |
| `notification_opened` / `notification_clicked` | backend, ao resolver o link com token | `notification_id`, `email_id?`, `origin` ∈ {`home`, `email`} |

`scope_effective` registra o valor de `notification_scope` aplicado ao gerar a notificação; `reasons[]` preserva os correlatos incluídos. Esses campos concretizam o conteúdo exigido pela issue-6.

Abertura de e-mail é medida **só pelo clique no link com token** — sem pixel de rastreamento. O resultado do adapter de prévia gera `notification_delivered_email` com `adapter: preview`, para que o fluxo completo seja observável no 1º ciclo mesmo sem SES.

## Confirmed facts

- 2026-09-20 (Eduardo): confirmou o corte local proposto e determinou que o documento AWS é a autoridade para disponibilidade de serviços. Os diagnósticos de 2026-09-18 abaixo são históricos.

- [[d14-data-operations-modeling]]: ingestão já emite lista de referências explícitas e lista de vizinhos por família ao final do job — fonte do evento de disparo de notificação.
- 2026-09-18 (issue-6): gatilho = qualquer documento novo indexado (família nova ou versão nova); escopo por usuário estrita/ampla sem padrão; conteúdo linka direto para trecho/versão; notificação estritamente informativa.
- 2026-09-18 (issue-8 / [[i2-model-serving]]): sem envio real de e-mail no 1º ciclo; único adapter ativo é a prévia na página inicial.
- Plano l.191: aceite do alerta = "frequência aplicada e sem duplicação no cenário testado".

## Decisions

- 2026-09-20 (issue-7, Eduardo): mantida telemetria local e explicitada a diferença entre prévia gerada e e-mail enviado.

- 2026-09-18 (issue-6): eventos `notification_generated`, `notification_delivered_home`/`_email`, `notification_opened`/`_clicked` existem desde o TB1.
- 2026-09-18 (issue-7): acrescentados `notification_suppressed` (com motivo) e `email_digest_generated`; `notification_delivered_email` carrega `adapter` e `email_id`.
- 2026-09-18 (issue-7): abertura de e-mail medida por clique em link com token; sem pixel.

## Derived requirements and constraints

- Para `adapter: preview`, resultado e interface não devem declarar entrega real de e-mail.

- `notification_generated` carrega o escopo efetivo do usuário e, no escopo ampla, os ids dos correlatos incluídos, para deduplicação e futuras análises de uso.
- Eventos de entrega distintos por canal permitem auditar as entregas. A issue-7 concretiza a prevenção de duplicações no backend, antes de `Mailer.send`, idempotente por `email_id`; os eventos registram o resultado dessa política.
- Todo evento carrega `user_id` e, quando aplicável, `notification_id`/`email_id`, para que "sem duplicação" seja auditável por consulta: nenhum `(user_id, document_version_id)` com dois `notification_generated`.
- `notification_delivered_email` é registrado pelo backend a partir do `DeliveryReport` devolvido por `Mailer.send`; o adapter só reporta ([[i9-integration]]).
- Chamadas reais ao SES (quando existirem) registram destinatário e `MessageId` — exigência de auditoria de custo em [[i11-cost]].
- Eventos persistem no Postgres local; nada de CloudWatch no 1º ciclo.

## Open questions

- (issue-6, detalhada pela issue-7) Os campos mínimos e o armazenamento estão definidos acima; o schema final é detalhe de implementação de F3 e não bloqueia a especificação.
- (issue-6/7) Telemetria de uso da busca (consultas, cliques em resultados, 👍/👎 de `POST /v1/feedback` da issue-5) ainda não foi tratada por nenhum Topic — esta página cobre só notificações.
- (issue-7) Se a ingestão virar contínua, `email_digest_generated` passa a ser por período, não por job.

## Evidence

- [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md), lido em 2026-09-20.
- Eduardo, 2026-09-20: “vamos seguir as sugestões” e “trate esse documento como autoridade para disponibilidade de serviços aws”.

- [[d14-data-operations-modeling]] (eventos de ingestão já existentes).
- Resposta de Eduardo, rodada 2 da issue #6 (2026-09-18): "aceito sugestões" (para os três eventos de telemetria propostos).
- Comentários de resolução das issues [#6](https://github.com/EricRLeao1311/CapiWatt/issues/6) e [#7](https://github.com/EricRLeao1311/CapiWatt/issues/7), seções "Telemetria".
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` l.50, 86, 112, 191.
- `hackathon/scripts/check_aws_capabilities.out` l.317–334 (SES negado; observação sobre sandbox).

## Topic history

- issue-7 (2026-09-20): revisão de disponibilidade aceita por Eduardo; inventário AWS incorporado como autoridade, corte local preservado. Mantidas as demais decisões desta página.

- issue-6: definiu os eventos base do ciclo de notificação (gerada, entregue home/e-mail, aberta/clicada); página original incorporada do commit `4f0e08a` de Eric.
- issue-7: acrescentou `notification_suppressed` e `email_digest_generated`, `adapter`/`email_id` na entrega por e-mail e abertura por clique com token. Sua versão local foi combinada com a base da issue-6.
