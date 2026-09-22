---
concern_id: d3-data-selection
concern: ~/.claude/skills/perspec-me/catalog/concerns/d3-data-selection/README.md
perspective: data
status: resolved
topics:
  - issue-10 — Quais tipos de documento compõem o caso 1 e quais metadados cada um precisa carregar?
updated_at: 2026-09-22
---

## Current resolution

O corpus inicial selecionado para o caso 1 cobre os três precedentes priorizados pela Carolina e quatro tipos documentais concretos: `auto_de_infracao` (incluindo a exposição de motivos que integra ou antecede o auto), `recurso_administrativo`, `complementacao_de_recurso` e `voto`. O processo administrativo é uma entidade agregadora do grafo, não uma família documental. Normas correlatas aparecem como referências estruturadas e não serão indexadas no primeiro ciclo; seus textos integrais não são necessários para a Destination atual.

Para cada precedente importante, o conjunto desejado é auto de infração, requerimento ou recurso quando houver, voto e, quando houver, nota técnica ou juízo de reconsideração. Recurso ou auto isolado não basta para sustentar o resultado: a seleção recuperável deve incluir documento decisório ou técnico que permita verificar fundamento e conclusão.

## Confirmed facts

- O corpus contém 3 autos/exposições de motivos, 3 recursos, 1 complementação de recurso e 3 votos, totalizando 10 PDFs.
- Os três processos de referência, por prioridade, são `48500.004024/2017-80`, `48500.000639/2019-07` e `48500.901433/2024-53`.
- O caso Coelba liga o processo de fiscalização impresso como `48500.001433/2024-53`, o NUP corrente `48500.901433/2024-53` e documentos próprios `48500.009907/2025-96` e `48500.017555/2025-42`.
- Não há, na entrega atual, PDF autônomo de norma, nota técnica ou juízo de reconsideração.
- O README considera insuficiente um recurso sem voto, nota técnica ou juízo de reconsideração, e também um auto sem documento decisório.

## Decisions

- 2026-09-22 (issue-10): o primeiro ciclo usa os 10 PDFs entregues como corpus concreto e trata os tipos ausentes previstos no gabarito como lacunas explícitas, não como documentos presumidos.
- 2026-09-22 (issue-10): normas citadas não são indexadas no primeiro ciclo; permanecem entidades de referência ligadas às peças por `regula`.

## Derived requirements and constraints

- A enumeração inicial de `document_type` deve conter `auto_de_infracao`, `exposicao_de_motivos`, `recurso_administrativo`, `complementacao_de_recurso`, `voto`, `nota_tecnica` e `juizo_de_reconsideracao`; os três últimos podem estar ausentes de um processo sem que o sistema invente sua existência.
- `processo_administrativo` deve ser modelado como nó agregador com peças relacionadas, nunca como família de versões de documento.
- Uma citação normativa deve ser extraída como entidade/relação com tipo, número, ano e dispositivo citado; seu texto integral não pertence ao corpus indexado do primeiro ciclo.
- O conjunto de resultados de um precedente deve indicar lacunas dos documentos indispensáveis e não apresentar recurso ou auto isolado como conjunto documental completo.
- A seleção precisa preservar os NUPs próprios de peças relacionadas sem separá-las do processo administrativo a que pertencem.

## Open questions

- Nenhuma questão material permanece para a Destination atual. Notas técnicas e juízos de reconsideração ausentes continuam registrados como lacunas e podem ser acrescentados posteriormente sem mudar a seleção mínima já decidida.

## Evidence

- `hackathon/data/case-1-carolina-mmgd/README.md` — inventário, Top 3, documentos indispensáveis e critérios de insuficiência.
- Os 10 PDFs entregues, cujos cabeçalhos confirmam os tipos e as ligações entre processos, autos, recursos, complementação e votos.

## Topic history

- issue-10: delimitou o corpus inicial, a taxonomia documental e as regras de suficiência e lacunas por precedente; excluiu a indexação de normas no primeiro ciclo.
