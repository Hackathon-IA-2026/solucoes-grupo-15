---
concern_id: u2-forcefulness
concern: ~/.claude/skills/perspec-me/catalog/concerns/u2-forcefulness/README.md
perspective: user-experience
status: resolved
topics:
  - issue-6 — O que dispara uma notificação (novo documento? mudança em processo acompanhado?) e o que ela contém na página inicial e no e-mail?
updated_at: 2026-09-18
---

## Current resolution

A notificação é estritamente informativa (decisão de Eduardo, 2026-09-18): avisa a Carolina sobre um documento novo (e, no escopo ampla, sobre seus correlatos) e não executa nem sugere nenhuma ação automática. A Carolina decide o que fazer a partir da notificação — abrir, ignorar, confirmar uma aresta sugerida (fluxo já existente na página do documento, [[u4-visualization]]).

A possibilidade de o sistema sugerir ou forçar uma ação a partir de uma notificação (ex.: marcar prioridade, sugerir revisão) foi explicitamente deixada de fora do TB1 (decisão de Eduardo, 2026-09-18).

## Confirmed facts

- Reunião de 2026-09-17 (Map issue #1): notificações previstas na home e por e-mail; forcefulness não havia sido especificada até esta decisão.

## Decisions

- 2026-09-18 (issue-6): notificação é puramente informativa; nenhuma ação automática ou sugerida a partir dela no TB1.

## Derived requirements and constraints

- A notificação nunca dispara efeito colateral (ex.: mudar status de processo, marcar decisão) — só leitura/navegação.
- Qualquer ação disponível a partir da notificação (ex.: confirmar aresta sugerida) é a mesma ação já disponível na página do documento ([[u4-visualization]]), nunca uma ação nova exclusiva da notificação.

## Open questions

- Sugestão/ação automática a partir de notificações — deixada para depois do TB1.

## Evidence

- Resposta de Eduardo, rodada 1 da issue #6 (2026-09-18): "Por hoje é estritamente informativa: avisar e deixar a Carolina decidir. Sugerir ação fica como pergunta futura, fora deste tópico."

## Topic history

- issue-6: fixou a notificação como estritamente informativa; adiou sugestão/ação automática para fora do TB1.
