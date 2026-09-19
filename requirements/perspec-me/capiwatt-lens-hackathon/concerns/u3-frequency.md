---
concern_id: u3-frequency
concern: ~/.claude/skills/perspec-me/catalog/concerns/u3-frequency/README.md
perspective: user-experience
status: partial
topics:
  - issue-6 — O que dispara uma notificação (novo documento? mudança em processo acompanhado?) e o que ela contém na página inicial e no e-mail?
  - issue-7 — Como a entrega de e-mail via SES lida com frequência e deduplicação?
updated_at: 2026-09-18
---

## Current resolution

O sistema decide quando notificar, não a Carolina (push, não pull) — decisão de Eduardo, 2026-09-18: **qualquer documento novo que possa gerar jurisprudência dispara uma notificação**, não apenas documentos ligados a um processo/família que ela já acompanha (rejeita explicitamente um filtro por "segue"). O evento de disparo é a indexação de um documento no corpus do caso 1 (job de ingestão, [[d14-data-operations-modeling]]).

Além do disparo, cada usuário (não só a Carolina) escolhe o **escopo** do que sua notificação inclui:
- **Estrita** — notificação apenas sobre aquele processo/família.
- **Ampla** — notificações gerais: inclui correlatos (famílias/processos ligados por aresta `referencia`, `similar_a`, e os tipos finos `revoga`/`altera`/`responde_a`/`regula`, recém-produzida pela mesma etapa de ingestão que introduziu o documento novo, [[d14-data-operations-modeling]]).

**Sem padrão implícito** (decisão de Eduardo, 2026-09-18): não existe valor default para `notification_scope`. Cada usuário precisa escolher explicitamente um dos dois tipos antes de o sistema gerar notificações para ele — a escolha é obrigatória, nunca inferida ou pré-selecionada.

"Documento novo" inclui tanto uma família nova quanto uma nova versão adicionada a uma família existente (decisão de Eduardo, 2026-09-18) — ambas contam como evento de disparo.

No escopo ampla, correlatos `suggested` (arestas `similar_a` ainda não confirmadas) entram na notificação junto com os `confirmed`, distintos visualmente como já ocorre na página da família ([[u4-visualization]]), em ambos os canais (home e e-mail) — decisão de Eduardo, 2026-09-18. Confirmar/rejeitar uma aresta `suggested` continua acontecendo só na página da família, nunca na notificação ([[u2-forcefulness]]).

A frequência de entrega por e-mail foi definida na issue #7: home imediata, um digest por (usuário, job de ingestão), deduplicação por `(user_id, document_version_id)` e `reindex` sem nova notificação. A política fica no backend antes do port `Mailer` ([[i9-integration]], [[i6-telemetry]]); no primeiro ciclo, o adapter ativo é a prévia, pois SES está indisponível (issue #8). Essas decisões complementam o gatilho e o escopo definidos aqui.

## Confirmed facts

- [[d14-data-operations-modeling]]: relações (explícitas e `similar_a`) são produzidas no fim do job de ingestão, no mesmo momento em que um documento novo entra no corpus — o conjunto de correlatos de um documento novo já está disponível no instante do disparo.
- Explícitas nascem `confirmed`; `similar_a` nasce `suggested` ([[i4-storage]], campo `status` de `document_relations`).

## Decisions

- 2026-09-18 (issue-6): disparo = qualquer documento novo indexado no corpus do caso 1 (família nova ou nova versão de família existente), não filtrado por "acompanhamento"; é o sistema quem decide notificar.
- 2026-09-18 (issue-6): cada usuário escolhe o escopo da sua notificação — estrita (só aquele processo/família) ou ampla (notificações gerais, com correlatos via aresta).
- 2026-09-18 (issue-6): `notification_scope` não tem valor padrão — a escolha é obrigatória para cada usuário antes de receber notificações.
- 2026-09-18 (issue-6): no escopo ampla, correlatos `suggested` e `confirmed` aparecem juntos na notificação, distintos visualmente; a ação de confirmar/rejeitar fica só na página da família.

## Derived requirements and constraints

- Existe uma preferência de escopo de notificação por usuário (`notification_scope: estrita | ampla`, sem default), lida no momento de montar cada notificação — não uma escolha feita notificação a notificação.
- Nenhuma notificação é gerada para um usuário antes de ele ter escolhido explicitamente seu `notification_scope` — o sistema precisa de um passo que force essa escolha (ex.: configuração obrigatória no primeiro acesso à área de notificações) antes de habilitar o recurso para aquele usuário.
- No escopo ampla, os correlatos incluídos são exatamente as arestas que a etapa de relações do job de ingestão já produziu para aquele documento/família no momento do disparo — nenhuma consulta adicional é feita fora desse conjunto.
- Correlatos com alvo fora do corpus (aresta pendente de alvo, [[d14-data-operations-modeling]]) não aparecem no escopo ampla — não há página para linkar.

## Open questions

- Onde exatamente na interface o usuário faz a escolha obrigatória de escopo (tela de onboarding, configurações, primeira visita à área de notificações) — detalhe de F1, não bloqueia a especificação.

## Evidence

- Comentário de resolução da [issue #7](https://github.com/EricRLeao1311/CapiWatt/issues/7): frequência e deduplicação da entrega por e-mail.
- Resposta de Eduardo, rodada 1 da issue #6 (2026-09-18).
- Resposta de Eduardo, rodada 2 da issue #6 (2026-09-18): "a seleção da notificação do tipo de notificação não deve ter um padrão, a carolina (ou qualquer usuário) deve sempre escolher um dos tipos de notificação."
- Resposta de Eduardo, rodada 3 da issue #6 (2026-09-18): "no escopo ampla, os correlatos suggested entram na notificação junto com os confirmed, distintos visualmente como na página da família, em ambos os canais. Confirmar/rejeitar continua acontecendo só na página da família."
- [[d14-data-operations-modeling]], [[i4-storage]], [[u4-visualization]] — momento e forma de produção das arestas, e o padrão visual confirmed/suggested reaproveitado.

## Topic history

- issue-7: definiu home imediata, digest por usuário/job e deduplicação no backend, sem alterar o gatilho ou a escolha obrigatória de escopo da issue-6.
- issue-6: fixou o disparo (qualquer documento novo, incluindo nova versão de família existente, não filtrado por acompanhamento), a escolha obrigatória (sem padrão) de escopo por usuário, e a inclusão de correlatos suggested+confirmed no escopo ampla.
