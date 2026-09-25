---
concern_id: o8-model-goals
concern: /home/eduardo/Documents/skills/skills/in-progress/perspec-me/catalog/concerns/o8-model-goals/README.md
perspective: system-objectives
status: resolved
topics:
  - issue-11 — Qual é o gabarito de priorização e como ele é usado para avaliar se os resultados mais relevantes aparecem no topo?
updated_at: 2026-09-22
---

## Current resolution

O objetivo de qualidade para a pergunta principal é recuperar, no topo, os processos de referência indicados pela Carolina dentro do corpus controlado de 10 PDFs, sem exigir uma ordem exata entre eles. Encontrar pelo menos dois dos três processos no Top 3 é o gate mínimo de aceitação; encontrar os três é a meta desejada. Além disso, cada processo recuperado deve expor todos os documentos indispensáveis disponíveis no corpus. Resolução aceita por Eduardo em 2026-09-22.

## Confirmed facts

- Carolina indicou três processos como referência de relevância para a pergunta principal.
- O bom resultado inicial descrito no material do caso é encontrar pelo menos dois precedentes sobre o tema, preferencialmente com decisão nos últimos três anos.
- Ordem imperfeita é tolerável no primeiro ciclo.
- O corpus atual não oferece base suficiente para extrapolar a qualidade para documentos ou consultas fora desse caso controlado.

## Decisions

- 2026-09-22 (issue-11): limitar o objetivo mensurável do primeiro ciclo ao corpus de avaliação em `hackathon/data/case-1-carolina-mmgd/` e ao Top 3 indicado pela Carolina.
- 2026-09-22 (issue-11): não exigir uma ordenação exata entre os três processos-gabarito.
- 2026-09-22 (issue-11, aceite de Eduardo): adotar `2/3` no Top 3 como gate mínimo, `3/3` como meta desejada e completude documental como gate obrigatório separado.

## Derived requirements and constraints

- O resultado da avaliação deve ser descrito como validade no corpus controlado, sem alegar cobertura da totalidade dos acervos ANEEL/SEI.
- O objetivo deve distinguir gate mínimo de meta desejada para que “dois precedentes úteis” não seja confundido com recuperação completa do gabarito.
- A meta precisa ser verificável por execução e não depender de julgamento retroativo sobre a ordem.
- O atendimento ao gate mínimo não pode ser apresentado como recuperação completa do gabarito; o relatório deve distinguir explicitamente `2/3` de `3/3`.
- 2026-09-25: a preferência por decisão nos últimos três anos é **critério de utilidade, não objetivo mensurável**. Ela não entra no gate nem em métrica ([[m5-performance-metrics]]): dois dos três processos-gabarito são mais antigos que isso, então medí-la reprovaria o gabarito. A interface pode exibir a data para o advogado julgar; o sistema não ordena nem filtra por ela.

## Open questions

- Nenhuma questão material permanece para a Destination atual.

## Evidence

- Issue #14, comentário “Resolução da entrega da Carolina”.
- `hackathon/data/case-1-carolina-mmgd/README.md` — Top 3 e definição de bom resultado inicial.
- Sessão `perspec-me` da issue #11, resposta de Eduardo em 2026-09-22.

## Topic history

- issue-11: delimitou o objetivo ao corpus controlado, definiu gate mínimo `2/3`, meta `3/3`, ordem interna livre e completude documental obrigatória em gate separado; resolução aceita por Eduardo em 2026-09-22.
