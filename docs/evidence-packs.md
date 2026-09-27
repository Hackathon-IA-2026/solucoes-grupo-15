# Evidence packs: prova em vez de narrativa

Sempre que um agente termina uma issue — ou precisa parar no meio de um trabalho longo — este projeto publica um **evidence pack**: um comentário auditável na própria issue, ligando cada critério de aceite a um comando real, um resultado real e um status honesto, em vez de um resumo em prosa dizendo "feito".

## Inspiração: por que exigir evidência

A prática segue a tese central do livro [*Agentic Software Engineering*](https://agenticse-book.github.io/), de Ahmed E. Hassan: em um cenário com colaboradores estocásticos (agentes de IA) e humanos, "produzir código não é o gargalo — o desafio real é complexidade, comunicação e manter a integridade do sistema ao longo do tempo", e times que "estabelecem intenção clara, gerenciam limites de risco e **exigem evidência**" vencem — não os que digitam mais rápido. O livro não prescreve o formato do pacote de evidências; isso é decisão da skill descrita abaixo.

## A skill

A skill [`evidence`](https://github.com/Esduard/skills/tree/main/skills/engineering/evidence) implementa essa exigência de forma concreta:

- extrai **claims** verificáveis dos critérios de aceite (nunca "implementação concluída" como sua própria evidência);
- monta um **scope-to-proof map** — cada claim ligada à fonte, ao comando de verificação e a um status de um vocabulário fechado de seis valores (`PASS`, `FAIL`, `PARTIAL`, `NOT_RUN`, `NOT_APPLICABLE`, `UNKNOWN` — nunca arredondado para `PASS` quando o valor real é `NOT_RUN`/`UNKNOWN`);
- registra evidência negativa (testes falhos, checagens puladas, suposições não resolvidas) com a mesma visibilidade que a positiva;
- publica o pacote como comentário na issue, com um marcador de idempotência (`<!-- evidence-pack:<issue>:<revisão> -->`) para atualizar em vez de duplicar numa regeneração.

## Como isso aparece neste repositório

**Ao terminar uma issue** — a skill `implement` deste mesmo catálogo instrui explicitamente: "Once committed, run `/evidence` to close out". Foi o que aconteceu ao final desta própria issue de documentação: [evidence pack publicado na #85](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/85#issuecomment-5851265288).

**Ao abortar um trabalho longo** — caso real da [#72 (rota de OCR para PDF escaneado)](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/72): o quinto critério de aceite exigia contar páginas escaneadas no corpus inteiro (1644 documentos), um processo demorado. A sessão foi interrompida a pedido explícito do coordenador antes de o script terminar. Em vez de silenciar isso, o agente publicou um [evidence pack com status geral `PARTIAL`](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/72#issuecomment-5850435844) — quatro dos cinco critérios em `PASS` com prova real, o quinto explicitamente `PARTIAL/NOT_RUN`, com o número exato de documentos já processados (800/1644) antes do corte. Numa sessão posterior, o script foi deixado terminar e um [segundo evidence pack, agora `PASS`](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/72#issuecomment-5851350818), fechou o critério pendente (1644/1644 documentos, 406 com página escaneada, 4.857 páginas escaneadas de 42.867) sem reexecutar o que já tinha prova.

## Por que isso importa

O caso da #72 é o argumento mais concreto para a prática: um agente que para no meio de um trabalho de longa duração — por corte de tempo, por pedido do coordenador, ou por qualquer outro motivo — ainda assim deixa um registro verificável do que estava provado e do que não estava, em vez de um "quase terminei" não verificável. Isso é o que torna seguro retomar o trabalho depois (ou por outra pessoa/agente): o próximo pack não reconfirma o que já tem prova, só fecha a lacuna registrada.
