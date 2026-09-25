---
concern_id: m5-performance-metrics
concern: /home/eduardo/Documents/skills/skills/in-progress/perspec-me/catalog/concerns/m5-performance-metrics/README.md
perspective: model
status: resolved
topics:
  - issue-11 — Qual é o gabarito de priorização e como ele é usado para avaliar se os resultados mais relevantes aparecem no topo?
updated_at: 2026-09-22
---

## Current resolution

A qualidade do ranking é medida, no corpus controlado de 10 PDFs, por `Recall@3` sobre processos agregados: quantidade de processos-gabarito presentes nos três primeiros resultados distintos, dividida por três. A ordem entre os três não importa. O gate mínimo é `2/3` (`Recall@3 >= 0,67`) e a meta desejada é `3/3` (`Recall@3 = 1`). A completude dos documentos disponíveis é verificada separadamente. Métricas de precisão permanecem informativas enquanto não houver exemplos irrelevantes ou difíceis no corpus. Resolução aceita por Eduardo em 2026-09-22.

## Confirmed facts

- O gabarito da pergunta principal contém três processos relevantes.
- Com três itens relevantes, a cobertura observável varia em passos de `1/3`: 0%, 33,3%, 66,7% ou 100%.
- A meta anterior de cobertura de pelo menos 95% equivale, neste gabarito, a exigir os três processos.
- Se o denominador permanecer fixo em cinco resultados, a relevância máxima no Top 5 é 60% quando existem somente três processos-gabarito; portanto, a meta anterior de 80% não é atingível nessa unidade.
- O README do corpus considera bom resultado inicial encontrar pelo menos dois precedentes sobre o tema e considera tolerável, no primeiro ciclo, uma ordem imperfeita.

## Decisions

- 2026-09-22 (issue-11): a avaliação usa o corpus reduzido e o Top 3 da Carolina, sem exigir igualdade exata da ordem dos resultados.
- 2026-09-22 (issue-11, aceite de Eduardo): usar `Recall@3` por processo agregado, com gate mínimo de `2/3` e meta desejada de `3/3`.
- 2026-09-22 (issue-11, aceite de Eduardo): manter a completude documental como gate obrigatório separado e métricas de precisão apenas como informação no corpus atual.
- 2026-09-25 (sessão de verificação do mapa, Eduardo): a recência é preferência de utilidade, nunca gate nem componente de métrica. Razão decisiva: dois dos três processos-gabarito (`48500.004024/2017-80` e `48500.000639/2019-07`) têm mais de três anos — um gate de recência reprovaria o próprio gabarito.

## Derived requirements and constraints

- Toda métrica deve declarar a unidade avaliada, o valor de `k`, o denominador e os identificadores retornados em cada posição.
- A recuperação do processo e a completude das classes documentais devem ser reportadas separadamente para que um PDF isolado não faça um precedente incompleto parecer correto.
- O resultado bruto ordenado da busca deve ser preservado junto de `corpus_version`, `model_version` e `ranking_version`.
- As metas de cobertura ≥95% e relevância no Top 5 ≥80% do plano precisam ser substituídas ou reinterpretadas para este corpus antes de servirem como gate.
- A execução passa no gate de recuperação quando pelo menos dois dos três processos-gabarito aparecem entre os três primeiros processos distintos; atingir os três é registrado como a meta completa.
- A avaliação deve colapsar documentos, chunks e NUPs relacionados no identificador do processo agregado antes de calcular `Recall@3`.
- `Precision@5` não é gate para este corpus, porque só existem três processos-gabarito e não há conjunto negativo representativo.
- 2026-09-25: **a recência não é gate e não entra em nenhuma métrica.** A preferência por decisão nos últimos três anos ([[o7-user-goals]]) é critério de utilidade para a Carolina, não critério de aceitação da execução. Nenhuma métrica pondera, filtra ou penaliza por data.

## Open questions

- Nenhuma questão material permanece para a Destination atual. Novos exemplos negativos ou novas perguntas de teste exigirão recalibrar as métricas, sem invalidar esta baseline.

## Evidence

- `hackathon/data/case-1-carolina-mmgd/README.md` — Top 3, bom resultado inicial, tolerância a ordem imperfeita e inventário documental.
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md`, seção “Indicadores e evidências de aceitação” — metas anteriores de cobertura e relevância no Top 5.
- Sessão `perspec-me` da issue #11, resposta de Eduardo em 2026-09-22.

## Topic history

- issue-11: definiu `Recall@3` por processo agregado, gate mínimo `2/3`, meta `3/3`, ordem interna livre e completude documental como gate separado; resolução aceita por Eduardo em 2026-09-22.
