---
concern_id: d11-consistency
concern: ~/.claude/skills/perspec-me/catalog/concerns/d11-consistency/README.md
perspective: data
status: partial
topics:
  - issue-3 — Como uma família de versões de um documento é identificada e agrupada num único objeto, na ingestão e no resultado da busca?
  - issue-28 — Como a busca pagina resultados ordenados por relevância em lotes de 10 sem alterar a ordem entre páginas?
  - issue-64 — Ao remover o conceito de família de documentos, como versões e documentos passam a ser identificados, agrupados e exibidos na ingestão, busca e interface?
updated_at: 2026-09-26
---

## Current resolution

Consistência aqui significa que **a mesma peça documental nunca aparece como duas coisas** e que **duas peças distintas nunca viram uma só sem confirmação humana**:

- Uma versão pertence a exatamente uma família. ~~Uma família nunca é dividida entre dois cards de resultado.~~ **Superado pela issue-64 (2026-09-26, Eduardo):** a busca não deduplica por peça na visualização — duas versões da mesma família podem aparecer como cards separados; o invariante de "no máximo um card por família" deixou de existir (ver [[u4-visualization]]).
- Reingerir o mesmo arquivo (checksum idêntico) não cria nova versão nem reindexa (idempotência do `index`, issue #2; LoD 3 do plano, linha 190).
- A chave explícita de família é estável entre ingestões: o mesmo `tipo + identificador oficial` sempre resolve para o mesmo `family_id`.
- O agrupamento por similaridade **só sugere** (decisão de Eduardo, 2026-09-18) — o sistema nunca funde famílias por conta própria, então um falso positivo de similaridade nunca corrompe silenciosamente a base; o custo aceito é que versões sem chave explícita fiquem separadas até alguém confirmar.
- Processo SEI não é família: suas peças são documentos distintos ligadas por aresta (issue #4), o que evita que uma juntada nova seja tratada como "nova versão" de outra peça.
- Uma sugestão de fusão pendente **não altera o agrupamento** na busca: as duas famílias continuam como dois cards, cada um com aviso "possível versão de …" (decisão de Eduardo, 2026-09-18). Só a aceitação, registrada com autoria, funde — via `reassign_family` no serviço vetorial, sem reembedding.

## Confirmed facts

- Plano, linha 190 (LoD 3): "uma ingestão adicional muda a base consultável sem duplicar a mesma versão".
- Issue #2: `index` idempotente por `(document_version, model_version)`.

## Decisions

- 2026-09-26 (issue-64, Eduardo): confirmado que os invariantes de dados abaixo (`document_version → family_id` como função; sugestão só funde com confirmação humana) continuam valendo por baixo da UI — a #64 remove só o agrupamento *visual*, não a identificação de dados ([[d4-data-dictionary]]).
- 2026-09-26 (issue-64, Eduardo): a busca não deduplica por peça — mais de um card da mesma família pode aparecer na mesma consulta. Supersede o invariante "cada família no máximo uma vez por consulta" (issue-2/issue-28).

- 2026-09-18 (issue-3): similaridade nunca funde famílias automaticamente; apenas gera sugestão.
- 2026-09-18 (issue-3): checksum idêntico é a definição de "mesma versão".
- 2026-09-18 (issue-3): sugestão pendente não muda o agrupamento; a fusão é uma reatribuição de família (não delete+reindex), auditável.

## Derived requirements and constraints

- Invariante: `document_version → family_id` é função; nenhuma versão em duas famílias.
- Invariante: nunca gerar sugestão de fusão entre famílias com chaves explícitas diferentes.
- Aceitar uma sugestão de fusão é uma operação auditável (quem, quando) e reversível o suficiente para o hackathon (ao menos registrada).
- ~~A `SearchResult` do serviço vetorial devolve cada família no máximo uma vez por consulta.~~ **Relocado pela issue-28 (2026-09-25)** e depois **removido pela issue-64 (2026-09-26):** o agrupamento por família no `backend` ([[i9-integration]]) deixa de existir na visualização; a busca não deduplica por peça e o invariante de "no máximo um card por família por consulta" não se aplica mais. O que resta em aberto é se algum invariante de ordenação estável entre lotes (issue-28) ainda se aplica sobre a nova unidade de paginação — ver [[i9-integration]].

## Open questions

- Limiar de similaridade para gerar sugestão — calibrar com os documentos reais do caso 1 (issue #13 escolhe o modelo de embeddings; o limiar é ajuste de implementação, não decisão de mapa).

## Evidence

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 162, 190.
- Issue #2, comentário de resolução.

## Topic history

- issue-3: fixou os invariantes de família/versão, a regra de que similaridade só sugere, e que sugestão pendente não altera o agrupamento na busca.
- issue-64: removeu o invariante "no máximo um card por família por consulta" — a busca não deduplica por peça na visualização; confirmou que os invariantes de dados subjacentes (chave/sugestão/fusão) permanecem intactos por baixo da UI.
