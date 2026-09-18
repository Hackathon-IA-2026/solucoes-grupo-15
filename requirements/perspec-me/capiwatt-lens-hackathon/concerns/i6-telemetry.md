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

O job de ingestão já emite os eventos de origem (documento indexado, aresta criada — [[d14-data-operations-modeling]]) que alimentam o disparo de notificação. Além desses, a própria notificação emite três eventos (decisão de Eduardo, 2026-09-18):

- `notification_generated` — documento/família gatilho, escopo aplicado (`estrita`/`ampla`) e lista de correlatos incluídos (quando ampla).
- `notification_delivered_home` / `notification_delivered_email` — um evento por canal de entrega.
- `notification_opened` / `notification_clicked` — interação do usuário, com o canal de origem.

Isso é o mínimo necessário para a issue #7 (dedup/frequência do e-mail) e, no futuro, para medir se os usuários usam as notificações.

## Confirmed facts

- [[d14-data-operations-modeling]]: ingestão já emite lista de referências explícitas e lista de vizinhos por família ao final do job — fonte do evento de disparo de notificação.

## Confirmed facts

- [[d14-data-operations-modeling]]: ingestão já emite lista de referências explícitas e lista de vizinhos por família ao final do job — candidato natural a fonte do evento de disparo de notificação.

## Decisions

- 2026-09-18 (issue-6): a notificação emite `notification_generated`, `notification_delivered_home`/`notification_delivered_email`, e `notification_opened`/`notification_clicked`.

## Derived requirements and constraints

- `notification_generated` carrega o `notification_scope` efetivo do usuário e, no escopo ampla, os ids dos correlatos incluídos — dado que a issue #7 e futuras análises de uso vão consumir.
- Um evento por canal de entrega (`notification_delivered_home`, `notification_delivered_email`) permite à issue #7 saber se um e-mail já foi enviado para aquele evento antes de reenviar.

## Open questions

- Formato/schema exato de cada evento (nomes de campo, onde é armazenado) — detalhe de implementação da issue #7 e de F3, não bloqueia a especificação.

## Evidence

- [[d14-data-operations-modeling]] (eventos de ingestão já existentes).
- Resposta de Eduardo, rodada 2 da issue #6 (2026-09-18): "aceito sugestões" (para os três eventos de telemetria propostos).

## Topic history

- issue-6: fixou os três eventos de telemetria que a notificação emite (geração, entrega por canal, interação).
