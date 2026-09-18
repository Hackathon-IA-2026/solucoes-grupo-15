---
concern_id: d11-consistency
concern: ~/.claude/skills/perspec-me/catalog/concerns/d11-consistency/README.md
perspective: data
status: partial
topics:
  - issue-3 — Como uma família de versões de um documento é identificada e agrupada num único objeto, na ingestão e no resultado da busca?
updated_at: 2026-09-18
---

## Current resolution

Consistência aqui significa que **a mesma peça documental nunca aparece como duas coisas** e que **duas peças distintas nunca viram uma só sem confirmação humana**:

- Uma versão pertence a exatamente uma família; uma família nunca é dividida entre dois cards de resultado.
- Reingerir o mesmo arquivo (checksum idêntico) não cria nova versão nem reindexa (idempotência do `index`, issue #2; LoD 3 do plano, linha 190).
- A chave explícita de família é estável entre ingestões: o mesmo `tipo + identificador oficial` sempre resolve para o mesmo `family_id`.
- O agrupamento por similaridade **só sugere** (decisão de Eduardo, 2026-09-18) — o sistema nunca funde famílias por conta própria, então um falso positivo de similaridade nunca corrompe silenciosamente a base; o custo aceito é que versões sem chave explícita fiquem separadas até alguém confirmar.
- Processo SEI não é família: suas peças são documentos distintos ligadas por aresta (issue #4), o que evita que uma juntada nova seja tratada como "nova versão" de outra peça.
- Uma sugestão de fusão pendente **não altera o agrupamento** na busca: as duas famílias continuam como dois cards, cada um com aviso "possível versão de …" (decisão de Eduardo, 2026-09-18). Só a aceitação, registrada com autoria, funde — via `reassign_family` no serviço vetorial, sem reembedding.

## Confirmed facts

- Plano, linha 190 (LoD 3): "uma ingestão adicional muda a base consultável sem duplicar a mesma versão".
- Issue #2: `index` idempotente por `(document_version, model_version)`.

## Decisions

- 2026-09-18 (issue-3): similaridade nunca funde famílias automaticamente; apenas gera sugestão.
- 2026-09-18 (issue-3): checksum idêntico é a definição de "mesma versão".
- 2026-09-18 (issue-3): sugestão pendente não muda o agrupamento; a fusão é uma reatribuição de família (não delete+reindex), auditável.

## Derived requirements and constraints

- Invariante: `document_version → family_id` é função; nenhuma versão em duas famílias.
- Invariante: nunca gerar sugestão de fusão entre famílias com chaves explícitas diferentes.
- Aceitar uma sugestão de fusão é uma operação auditável (quem, quando) e reversível o suficiente para o hackathon (ao menos registrada).
- A `SearchResult` do serviço vetorial devolve cada família no máximo uma vez por consulta.

## Open questions

- Limiar de similaridade para gerar sugestão — calibrar com os documentos reais do caso 1 (issue #13 escolhe o modelo de embeddings; o limiar é ajuste de implementação, não decisão de mapa).

## Evidence

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 162, 190.
- Issue #2, comentário de resolução.

## Topic history

- issue-3: fixou os invariantes de família/versão, a regra de que similaridade só sugere, e que sugestão pendente não altera o agrupamento na busca.
