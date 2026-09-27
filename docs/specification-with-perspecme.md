# Especificação orientada por concerns com PerspecMe

Este projeto especifica decisões de arquitetura e produto através de **PerspecMe**, uma skill de agente que conduz a especificação em torno de um catálogo de *concerns* (preocupações) em vez de perguntar "o que você quer?" de forma livre.

## Origem: metodologia acadêmica vs. skill vs. uso neste projeto

São três camadas distintas, que este documento não mistura:

1. **A metodologia acadêmica** — PerSpecML, de Hugo Villamizar e Mariana Kalinowski (PUC-Rio):

   > Villamizar, H., & Kalinowski, M. (2024, November). *Identifying concerns when specifying machine learning-enabled systems: A perspective-based approach.* In Proceedings of the XXIII Brazilian Symposium on Software Quality (pp. 673-675).

   Ela propõe examinar a especificação de sistemas com ML sob múltiplas perspectivas (objetivos do sistema, experiência do usuário, infraestrutura, modelo, dados), cada uma decomposta em *concerns* — lentes que apontam para algo que a especificação pode precisar endereçar.

2. **A skill `perspec-me`**, disponível em [`Esduard/skills` — `skills/in-progress/perspec-me`](https://github.com/Esduard/skills/tree/main/skills/in-progress/perspec-me), que implementa essa ideia como um catálogo de ~60 *concerns* organizados em 5 Perspectivas (O — System Objectives, U — User Experience, I — Infrastructure, M — Model, D — Data), mais um protocolo de entrevista e persistência que roda por cima desse catálogo.

3. **O uso concreto neste repositório** — o que este documento descreve.

## O que são concerns aqui

Um **Concern** é uma lente estável do catálogo (ex.: `I9 — Integration`, `U4 — Visualization`, `D16 — Golden dataset`) que descreve algo que a especificação pode precisar tratar. O catálogo é somente leitura: a skill nunca escreve nele, só na camada de resolução do projeto.

Cada Concern relevante para este caso tem uma **Resolution page** própria em [`requirements/perspec-me/capiwatt-lens-hackathon/concerns/`](../requirements/perspec-me/capiwatt-lens-hackathon/concerns/) — a síntese do que *este projeto* decidiu para aquele Concern, nunca a definição genérica do catálogo. Ela guarda decisões, fatos confirmados, requisitos derivados, perguntas em aberto e evidência, com um `status` obrigatório dentre sete estados fixos (`unexamined`, `open`, `partial`, `resolved`, `deferred`, `not-applicable`, `superseded`).

## Como concerns são selecionados e delimitam a especificação

Uma pergunta/decisão concreta (um **Topic**, ex. "Qual é o contrato do parecer jurídico conclusivo de uma frase?" — [issue #27](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/27)) é resolvida olhando o catálogo de forma progressiva: primeiro as 5 Perspectivas, depois só as Perspectivas plausíveis, depois só os 2-5 Concerns dentro delas que plausivelmente se aplicam. Isso evita ler os ~60 Concerns inteiros a cada rodada e mantém a especificação limitada ao que o catálogo já mapeou como relevante, em vez de partir de intuição livre do agente.

Um **Map** — [`MAP.md`](../requirements/perspec-me/capiwatt-lens-hackathon/MAP.md), ancorado na issue [#1 (mapa de decisões)](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/1) — indexa esse trabalho: uma tabela de cobertura por Perspectiva (quantos Concerns estão em cada estado), a **Frontier** (Topics abertos, desbloqueados, prontos para a próxima sessão) e o **Fog** (regiões que sabidamente importam mas ainda não podem ser fraseadas como pergunta precisa). Em 26/09/2026 a tabela do Map mostra, por exemplo, a Perspectiva I (Infraestrutura) com 7 Concerns em `partial` e 1 `resolved` — um retrato de quanto já foi examinado e quanto ainda não, sem precisar abrir cada Resolution page.

## Relação com issues e labels

Neste repositório, o vínculo Concern↔issue **não é feito por labels de GitHub por concern** (não existe, por exemplo, um label `concern:i9`) — ele vive no front-matter `topics:` de cada Resolution page. Um Concern pode ser tocado por várias issues ao longo do tempo: `I9 — Integration` acumula as issues [#2](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/2), [#3](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/3), [#4](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/4), [#7](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/7), [#15](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/15), [#28](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/28) e [#64](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/64); e uma issue pode tocar mais de um Concern (a revisão da issue #57 no Map atualizou D1 e U4 na mesma rodada).

O que *é* representado por labels é o mecanismo de tracker que sustenta o Map/Frontier: `wayfinder:map` marca a issue-mapa (#1), `wayfinder:task` marca um trabalho manual que destrava uma decisão (ex. [#14](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/14)), `wayfinder:prototype` marca um Topic resolvido construindo um protótipo em vez de só conversando (ex. [#59](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/59), [#60](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/60), [#61](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/61)), e `ready-for-agent` marca um Topic específico o bastante para um agente resolver sem supervisão síncrona. Um sinal característico desse fluxo, visível em várias issues abertas (ex. [#40](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/40)), é o próprio título ser fraseado como pergunta — refletindo que um Topic é a pergunta em si, não uma tarefa.

## Como isso reduz especificação ad hoc

Antes de entrevistar alguém, a skill precisa investigar evidência já existente no repositório (decisões anteriores, código, Resolution pages de Concerns já tocados) — a entrevista não parte do zero. E cada Resolution page é criada só na primeira vez que o Concern é tocado; uma sessão posterior **atualiza** o mesmo arquivo, nunca sobrescreve as decisões anteriores. Isso é visível na página de `I9 — Integration`: a decisão da issue #2 (agrupamento por família é obrigação do contrato do serviço) foi explicitamente **superseded** pela issue #28, que por sua vez teve sua unidade de paginação revista pela issue #64 — cada revisão registrada como decisão datada, com a anterior riscada e explicada, nunca apagada.

## Refinamento progressivo

O estado `partial` é o mais comum na tabela de cobertura do Map porque a especificação avança por rodadas: uma pergunta pode deixar parte do território de um Concern resolvido e registrar o resto em "Open questions" (ex. `I9`, em 26/09/2026, tem `partial` porque o campo de desempate na paginação por chunk ficou explicitamente em aberto após a issue #64). Isso é o que o glossário da skill chama de Concern state, e é diferente de "closed"/"done": `resolved` significa "entendimento suficiente para o Destination e escopo atuais", não permanente.
