---
concern_id: o2-need
concern: /home/eduardo/Documents/skills/skills/in-progress/perspec-me/catalog/concerns/o2-need/README.md
perspective: system-objectives
status: resolved
topics:
  - issue-12 — Qual é a pergunta/tarefa concreta do caso 1 e o que Carolina considera resposta útil e erro material?
updated_at: 2026-09-22
---

## Current resolution

A necessidade do TB1 é reduzir o esforço de localizar e acompanhar precedentes de fiscalização do atendimento a solicitações de conexão de MMGD, hoje espalhados entre SEI/ANEEL e Sicnet2 e difíceis de encontrar sem conhecer previamente números de processo, documento ou combinações exatas de palavras. O sistema cobre busca semântica verificável, organização das peças por processo, notificação de novos documentos e um parecer jurídico conclusivo de uma frase apoiado nas evidências recuperadas. A redação da peça jurídica completa continua com o advogado.

Esta síntese usa a resolução e a revisão posterior da issue #14 como autoridade indicada por Eduardo, refinada pela resposta da issue #12 em 2026-09-22. Histórico de buscas e favoritos são evolução posterior, fora da Destination atual.

## Confirmed facts

- Localizar precedentes aplicáveis leva atualmente pelo menos duas horas, sem incluir a análise de mérito.
- A pesquisa é feita sob demanda e exige navegar por SEI/ANEEL, Sicnet2/ANEEL, pautas da Diretoria e outras fontes auxiliares.
- SEI e Sicnet exigem frequentemente que a pessoa já saiba um número ou código; documentos de um mesmo processo podem ficar divididos entre os dois sistemas.
- A tarefa real inclui localizar precedentes e suas peças, verificar o último andamento e receber aviso quando um novo documento for juntado.
- O comentário posterior de Eduardo na issue #14 esclarece que o sistema faz busca semântica em documentos e não substitui o julgamento jurídico do advogado.

## Decisions

- 2026-09-22 (issue-12, Eduardo): usar o comentário de resolução da issue #14, incluindo sua revisão posterior, como resposta autoritativa para este Topic.
- A revisão posterior prevalece onde a primeira descrição atribui ao sistema conclusões ou resumos jurídicos que não pertencem ao TB1.
- 2026-09-22 (issue-12, Eduardo): incluir no TB1 um parecer jurídico conclusivo de uma frase, mas manter a redação da peça jurídica completa fora do sistema.
- 2026-09-22 (issue-12, Eduardo): tratar histórico de buscas e favoritos como evolução posterior, fora da Destination atual.

## Derived requirements and constraints

- A busca deve aceitar linguagem natural sem exigir que o usuário já conheça o número do processo ou documento.
- Resultados devem preservar vínculo verificável com processo, documento, versão, fonte e localizador.
- Peças relacionadas devem ser reunidas por processo mesmo quando o histórico atravessa Sicnet2 e SEI.
- O parecer de uma frase deve permanecer ligado às evidências recuperadas e não pode se expandir para redação autônoma da peça jurídica.
- A forma estruturada, os campos permitidos e a regra de abstenção do parecer serão definidos no Topic “Qual é o contrato do parecer jurídico conclusivo de uma frase e como ele permanece verificável?”.

## Open questions

- Nenhuma questão material permanece para a necessidade e a fronteira funcional tratadas neste Topic. O contrato detalhado do parecer segue em Topic próprio.

## Evidence

- Issue #14, comentário “Resolução da entrega da Carolina” e revisão posterior de Eduardo.
- `hackathon/data/case-1-carolina-mmgd/README.md` — tarefa real, dores atuais, perguntas de teste e experiência tradicional.
- Wayfinder Map, Destination e decisões já registradas sobre busca vetorial, agrupamento, grafo e notificações.

## Topic history

- issue-12: definiu busca, acompanhamento e parecer conclusivo de uma frase como parte do TB1; manteve redação de peças, histórico e favoritos fora da Destination atual.
