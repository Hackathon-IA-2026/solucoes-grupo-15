---
concern_id: d16-golden-dataset
concern: /home/eduardo/Documents/skills/skills/in-progress/perspec-me/catalog/concerns/d16-golden-dataset/README.md
perspective: data
status: resolved
topics:
  - issue-11 — Qual é o gabarito de priorização e como ele é usado para avaliar se os resultados mais relevantes aparecem no topo?
updated_at: 2026-09-22
---

## Current resolution

O golden dataset do primeiro ciclo é o corpus controlado de 10 PDFs em `hackathon/data/case-1-carolina-mmgd/`, não o conjunto anteriormente estimado em aproximadamente 100 documentos. Para a pergunta principal sobre precedentes de fiscalização do atendimento a solicitações de conexão de MMGD, os três processos indicados pela Carolina formam o conjunto-gabarito de relevância. Eles são um conjunto de referência, sem exigir ordem exata entre os três.

As classificações documentais registradas na issue #14 e no README do corpus integram o gabarito: autos/exposições de motivos, recursos e complementação, votos e as lacunas declaradas de nota técnica ou juízo de reconsideração. A unidade avaliada é o processo agregado, com os NUPs relacionados normalizados para o mesmo caso. A recuperação e a completude documental são gates separados. Esta resolução foi aceita por Eduardo em 2026-09-22.

## Confirmed facts

- O corpus de avaliação foi reduzido dos aproximadamente 100 documentos cogitados anteriormente para somente os 10 PDFs presentes em `hackathon/data/case-1-carolina-mmgd/`.
- Carolina indicou como Top 3 de referência os processos `48500.004024/2017-80`, `48500.000639/2019-07` e `48500.901433/2024-53`.
- Os dois primeiros processos têm auto de infração, recurso e voto no corpus; o terceiro tem auto/exposição de motivos e voto, além de recurso e complementação com NUPs próprios ligados ao mesmo caso Coelba/AI `0035/2025-SFT`.
- Não há PDF autônomo de nota técnica ou juízo de reconsideração no corpus atual.
- A issue #14 descreve o gabarito como referência de relevância, não como ranking exato.

## Decisions

- 2026-09-22 (issue-11, Eduardo): usar apenas os documentos de `hackathon/data/case-1-carolina-mmgd/` como corpus controlado de avaliação do primeiro ciclo.
- 2026-09-22 (issue-11, Eduardo): tratar os três processos indicados pela Carolina como o gabarito de relevância da pergunta principal.
- 2026-09-22 (issue-11): usar as classificações de documento registradas na issue #14 e no README do corpus como anotações do gabarito.
- 2026-09-22 (issue-11, aceite de Eduardo): avaliar por processo agregado, associando os NUPs de recurso e complementação ao caso Coelba de referência.
- 2026-09-22 (issue-11, aceite de Eduardo): manter a completude dos documentos disponíveis como gate obrigatório separado da recuperação do processo.

## Derived requirements and constraints

- O corpus e o gabarito precisam ser versionados juntos para que uma execução de avaliação possa ser reproduzida.
- A avaliação deve normalizar os NUPs e relacionar os recursos `48500.009907/2025-96` e `48500.017555/2025-42` ao caso de referência `48500.901433/2024-53`, sem contá-los como precedentes independentes.
- A ausência, no corpus, de nota técnica ou juízo de reconsideração deve permanecer explícita e não pode ser penalizada como falha de recuperação.
- A ordem interna dos três processos-gabarito não pode ser usada como exigência de igualdade exata do ranking.
- Para cada processo-gabarito recuperado, o resultado deve expor todos os documentos indispensáveis que estão disponíveis no corpus; tipos declaradamente ausentes permanecem lacunas e não contam como falha.

## Open questions

- Nenhuma questão material permanece para a Destination atual.

## Evidence

- Issue #14, comentário “Resolução da entrega da Carolina” e revisão posterior de Eduardo.
- `hackathon/data/case-1-carolina-mmgd/README.md` — pergunta principal, Top 3, inventário dos 10 PDFs, classificações documentais e critérios de suficiência.
- Sessão `perspec-me` da issue #11, resposta de Eduardo em 2026-09-22 sobre a redução do corpus e o uso do Top 3 como gabarito.

## Topic history

- issue-11: fixou o corpus controlado de 10 PDFs, o Top 3 como conjunto-gabarito, o processo agregado como unidade e a completude documental como gate separado; resolução aceita por Eduardo em 2026-09-22.
