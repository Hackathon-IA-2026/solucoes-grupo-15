---
concern_id: u4-visualization
concern: Visualização — cards de temas/famílias
perspective: user-experience
status: resolved
topics:
  - remover-contagem-documentos-temas
updated_at: 2026-09-27
---

## Current resolution

**Sessão direta (2026-09-27, Thiago):** Remove-se a exibição da contagem de documentos ("X documentos") dos cards de tema em toda a interface, assim como elementos de UI que dependem dessa métrica.

Na **landing page** (`ExploreLanding.tsx`): o texto "X documentos" some dos cards de tema em destaque.

Na **página Temas** (`FamiliesPage.tsx`):
- O texto "X documentos" some dos cards de tema
- A seção "Mais acessados" da sidebar é removida inteira (usava ordenação por `documents`)
- Os filtros segmentados "Todos | Mais acessados | Em alta" são removidos
- A barra de pesquisa por tema permanece

O campo `documents` no tipo `Family` e no mock `familias.ts` permanece inalterado — a mudança é apenas de visualização, não de estrutura de dados.

## Confirmed facts

- O campo `family.documents` era usado em 3 lugares de renderização: card na landing, card na página Temas, lista "Mais acessados"
- O campo também era usado para ordenar a seção "Mais acessados" (`sort((a,b) => b.documents-a.documents)`)
- Dados mockados não refletem realidade; exibir números fictícios pode confundir usuários

## Decisions

- 2026-09-27 (Thiago): remover toda exibição de contagem de documentos nos cards de tema
- 2026-09-27 (Thiago): remover seção "Mais acessados" (depende de métrica de documentos)
- 2026-09-27 (Thiago): remover filtros "Todos | Mais acessados | Em alta" (sem dados reais para sustentar)
- 2026-09-27 (Thiago): manter barra de pesquisa funcional
- 2026-09-27 (Thiago): remover sidebar "Tema em destaque" (card destacado era apenas visual, sem função)

## Derived requirements and constraints

- `ExploreLanding.tsx`: remover `<span className="landing-family-count">...</span>`
- `FamiliesPage.tsx`: remover `<footer><span>{family.documents...}</span>` dos cards
- `FamiliesPage.tsx`: remover bloco `<aside>` com "Mais acessados"
- `FamiliesPage.tsx`: remover `<div className="segmented-control">...</div>`
- CSS pode manter classes (não quebra nada); limpeza de CSS morto é opcional

## Open questions

- Nenhuma — escopo bem definido e localizado

## Evidence

- Screenshot da landing page mostrando "1.284 documentos", "982 documentos" etc. nos cards
- Screenshot dos filtros "Todos | Mais acessados | Em alta" na página Temas

## Topic history

- remover-contagem-documentos-temas: fixou remoção de toda exibição de contagem de documentos e elementos dependentes dessa métrica

- 2026-09-27 (Thiago): não alterar tipo TypeScript nem mock (mudança cosmética)
