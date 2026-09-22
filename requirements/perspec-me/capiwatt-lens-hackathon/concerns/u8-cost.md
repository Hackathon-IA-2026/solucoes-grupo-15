---
concern_id: u8-cost
concern: /home/eduardo/Documents/skills/skills/in-progress/perspec-me/catalog/concerns/u8-cost/README.md
perspective: user-experience
status: partial
topics:
  - issue-12 — Qual é a pergunta/tarefa concreta do caso 1 e o que Carolina considera resposta útil e erro material?
updated_at: 2026-09-22
---

## Current resolution

Para o TB1, erro material do sistema é uma falha de recuperação, associação, notificação ou geração do parecer capaz de levar o advogado à evidência ou conclusão errada, ou de ocultar uma juntada relevante. O gate confirmado nesta issue inclui confundir a distribuidora, associar ou citar número de processo errado, relacionar a norma errada à penalidade e deixar de notificar novo andamento porque o documento não foi indexado ou o módulo de notificação falhou. Documento restrito ou indisponível deve ser sinalizado explicitamente como requisito obrigatório separado.

A falha mais perigosa é não avisar a juntada de um auto de infração, pois o cliente pode ter prazo de dez dias corridos para recurso. O TB1 agora também produz um parecer jurídico conclusivo de uma frase; portanto, situação da penalidade, valores e demais campos gerados precisam de contrato estruturado, evidência e regra de abstenção próprios. Esse detalhamento segue na issue #27, mantendo este Concern `partial`.

## Confirmed facts

- A issue #14 lista erros jurídicos graves e um comentário posterior de Eduardo distingue quais deles o sistema de busca pode efetivamente cometer.
- Os erros atribuíveis ao sistema nessa revisão são: confundir distribuidora, citar processo errado, apontar norma errada ligada à penalidade e falhar em notificar novo andamento.
- Não notificar a juntada de auto de infração pode comprometer prazo de dez dias corridos para recurso.
- Documento restrito ou indisponível deve ser mostrado como `documento com acesso restrito`, nunca omitido silenciosamente.
- Resumo incompleto, precedentes antigos e ordem imperfeita são toleráveis no primeiro ciclo, dentro dos gates já definidos para recuperação.

## Decisions

- 2026-09-22 (issue-12, Eduardo): a resolução revisada da issue #14 é a autoridade para delimitar erro material.
- A revisão posterior separa erros da atividade jurídica humana de erros que o sistema de recuperação e notificação pode causar.
- 2026-09-22 (issue-12, Eduardo): confirmar os quatro erros sugeridos como gate de erro material e manter o aviso de acesso restrito como requisito obrigatório separado.
- 2026-09-22 (issue-12, Eduardo): incluir parecer jurídico conclusivo de uma frase no TB1, mantendo a redação da peça fora.
- PydanticAI foi sugerido como apoio possível para saídas estruturadas com Enums; a biblioteca e o contrato ainda não foram escolhidos.

## Derived requirements and constraints

- Identificadores de processo, distribuidora e norma exibidos precisam resolver para a evidência documental correspondente.
- O sistema não pode ocultar ausência ou restrição de acesso; deve informar explicitamente a indisponibilidade.
- A ingestão e a notificação precisam tornar observável a juntada de auto de infração, com prioridade compatível com o risco de prazo.
- Avaliações do TB1 devem testar associações erradas entre documentos semanticamente semelhantes, não apenas ausência de resultados.
- O produto deve manter a distinção entre evidência recuperada e interpretação do advogado.
- Cada penalidade, situação e valor no parecer deve resolver para evidência documental; se a evidência necessária faltar ou conflitar, o sistema deve abster-se em vez de completar por inferência não sustentada.

## Open questions

- Issue #27: quais campos e Enums compõem o parecer de uma frase, como cada campo cita sua evidência e em quais condições o sistema deve abster-se?
- Issue #27: erros de situação ou valor da penalidade entram no mesmo gate de erro material ou em um gate específico para o parecer?

## Evidence

- Issue #14, seção “Erro material” e comentário posterior de Eduardo restringindo os erros atribuíveis ao sistema.
- `hackathon/data/case-1-carolina-mmgd/README.md`, seções “Erro material” e “Experiência tradicional”.
- Wayfinder Map, decisões de notificações das issues #6 e #7.

## Topic history

- issue-12: confirmou o gate dos quatro erros de recuperação/notificação, o aviso obrigatório de acesso restrito e a inclusão do parecer de uma frase; o risco específico da geração estruturada segue na issue #27.
