---
concern_id: i10-hybrid-decision-intelligence
concern: ~/.claude/skills/perspec-me/catalog/concerns/i10-hybrid-decision-intelligence/README.md
perspective: infrastructure
status: partial
topics:
  - issue-4 — Como as relações entre documentos são representadas (arestas, origem: metadado explícito vs. similaridade) e onde ficam armazenadas?
updated_at: 2026-09-18
---

## Current resolution

Para relações entre documentos, **regra explícita decide, modelo só sugere** — o mesmo padrão que a issue #3 fixou para famílias de versões (decisão de Eduardo, 2026-09-18):

- Uma aresta com `origin: explicit` (metadado da fonte ou identificador reconhecido no texto e resolvido pela chave `tipo + identificador oficial`) nasce com `status: confirmed`, carregando evidência (versão + localizador). Nenhuma confirmação humana é exigida.
- Uma aresta com `origin: similarity` (vizinhança vetorial) nasce com `status: suggested`, aparece na interface como tal (aresta tracejada, distinta das confirmadas) e só passa a `confirmed` por aceite humano com autoria; pode ser `rejected`, o que impede nova sugestão para o mesmo par. **A similaridade nunca cria aresta confirmada por conta própria.**
- Quando as duas origens produzem a mesma aresta (par + tipo), a explícita prevalece e a sugestão de similaridade é absorvida (não coexistem duas arestas para o mesmo par/tipo).
- A saída do modelo é filtrada por regras antes de virar aresta: candidatos acima do limiar de fusão são desviados para sugestão de fusão de família (#3); o restante acima do limiar de relação vira `similar_a` sugerida; top-k por família.

## Confirmed facts

- Issue #3 ([[d11-consistency]]): similaridade nunca funde famílias automaticamente; sugestão pendente não altera o comportamento da busca; aceite com autoria.
- Reunião de 2026-09-17: relações entre documentos são um grafo explorável na interface — o usuário verá as arestas e, portanto, precisa distinguir confirmadas de sugeridas.

## Decisions

- 2026-09-18 (issue-4): `origin: explicit` ⇒ `status: confirmed` automático com evidência; `origin: similarity` ⇒ `status: suggested`, confirmação humana com autoria.
- 2026-09-18 (issue-4): aresta explícita prevalece sobre sugestão de similaridade para o mesmo par/tipo.
- 2026-09-18 (issue-4): a saída do modelo passa por regras (limiar de fusão vs. limiar de relação, top-k) antes de virar aresta.

## Derived requirements and constraints

- Estados de aresta: `confirmed | suggested | rejected`; transição `suggested → confirmed/rejected` registra quem e quando.
- A interface distingue visualmente aresta confirmada de sugerida e oferece aceitar/rejeitar na própria aresta (detalhe de UI na issue #5).
- Invariante: nenhuma aresta `origin: similarity` está em `status: confirmed` sem registro de autoria.
- Invariante: no máximo uma aresta por (origem, destino, tipo).

## Open questions

- Se uma aresta explícita for contestada pelo usuário (identificador mal resolvido), existe "rejeitar aresta explícita"? Hoje não previsto; decidir quando houver caso real.

## Evidence

- `concerns/d11-consistency.md`, `concerns/d4-data-dictionary.md` (issue #3).
- Map issue #1, Notes: "Relações entre documentos modeladas como grafo explorável na interface".

## Topic history

- issue-4: fixou o padrão explícito-decide/similaridade-sugere para arestas, os estados de aresta e a precedência da origem explícita.
