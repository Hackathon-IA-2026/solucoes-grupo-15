---
concern_id: o7-user-goals
concern: /home/eduardo/Documents/skills/skills/in-progress/perspec-me/catalog/concerns/o7-user-goals/README.md
perspective: system-objectives
status: resolved
topics:
  - issue-12 — Qual é a pergunta/tarefa concreta do caso 1 e o que Carolina considera resposta útil e erro material?
updated_at: 2026-09-22
---

## Current resolution

Para a pergunta principal — “procure precedentes sobre fiscalização de atendimento a solicitações de conexão de MMGD” — Carolina quer encontrar pelo menos dois precedentes aplicáveis, preferencialmente com decisão nos últimos três anos, e navegar pelas peças que permitem ao advogado avaliar cada caso. Uma resposta útil entrega processos distintos com PDFs, números oficiais, fonte e documentos indispensáveis disponíveis, permite verificar o último andamento, avisa novas juntadas e exibe um parecer conclusivo de uma frase apoiado nos documentos.

O parecer pode assumir forma como “manter a penalidade de advertência; manter o valor total das penalidades de multa de R$ 13.035.844,59”. O sistema não redige a peça jurídica completa. Histórico de buscas e favoritos permanecem como evolução posterior, fora da Destination atual.

## Confirmed facts

- A pergunta principal e as perguntas adicionais estão registradas na issue #14 e no README do corpus.
- Bom resultado inicial significa encontrar pelo menos dois precedentes, preferencialmente recentes, com PDFs e números SEI/Sicnet.
- Para um processo importante, auto de infração, recurso quando houver, voto e documento técnico ou de reconsideração quando houver compõem o conjunto desejado.
- Recurso sem documento decisório ou técnico, e auto sem documento decisório, são insuficientes isoladamente.
- Carolina também deseja aviso de andamento em até duas horas após o documento constar na ANEEL e evitar consulta manual diária.

## Decisions

- 2026-09-22 (issue-12, Eduardo): a resposta da issue #14 é a fonte autoritativa para a tarefa e para a definição de resposta útil.
- A utilidade é avaliada pela recuperação de evidência verificável e suficiente para análise humana, não pela geração de conclusão jurídica.
- 2026-09-22 (issue-12, Eduardo): a resposta útil inclui um parecer jurídico conclusivo de uma frase; a redação da peça fica fora do TB1.
- 2026-09-22 (issue-12, Eduardo): histórico de buscas e favoritos ficam fora da Destination atual como evolução posterior.

## Derived requirements and constraints

- Cada resultado útil deve identificar o processo, disponibilizar os PDFs e expor os identificadores oficiais e a origem.
- O resultado deve reunir as peças disponíveis por processo e indicar lacunas, sem apresentar documento isolado como conjunto completo.
- A interface deve deixar o advogado navegar da lista de precedentes aos documentos e trechos que justificam a correspondência.
- A notificação deve apontar para o novo documento e seu processo, preservando data, PDF e vínculo verificável.
- O parecer de uma frase deve apontar para as evidências que sustentam a conclusão e separar valores, tipos de penalidade e situação decisória em estrutura validável.

## Open questions

- Nenhuma questão material permanece para o objetivo do usuário tratado neste Topic. O contrato estruturado e a abstenção do parecer seguem na issue #27.

## Evidence

- Issue #14, comentário “Resolução da entrega da Carolina” e revisão posterior de Eduardo.
- `hackathon/data/case-1-carolina-mmgd/README.md` — perguntas de teste, gabarito, suficiência documental e bom resultado inicial.
- Issue #11 — gate mínimo de dois processos no Top 3, meta de três e completude documental em gate separado.

## Topic history

- issue-12: definiu a resposta útil como recuperação de pelo menos dois precedentes com evidência verificável, peças disponíveis e parecer conclusivo de uma frase; redação de peças, histórico e favoritos ficaram fora da Destination atual.
