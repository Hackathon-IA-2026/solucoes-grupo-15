---
concern_id: u6-acceptance
concern: ~/.claude/skills/perspec-me/catalog/concerns/u6-acceptance/README.md
perspective: user-experience
status: partial
topics:
  - issue-5 — Como a interface expõe a exploração do grafo de relações e o objeto-documento com versões, a partir dos protótipos juridico_wallace?
updated_at: 2026-09-18
---

## Current resolution

O usuário aceita o grafo e a busca porque cada relação e cada trecho mostram de onde vieram (decisão de Eduardo, 2026-09-18). Uma regra só, aplicada em todo lugar:

- Aresta explícita (`origin: explicit`, estado `confirmed`) leva o selo "explícita". Ao clicar, a interface abre o trecho da versão e o localizador onde a referência foi encontrada, e o usuário pode ir até ele.
- Aresta `similar_a` (estado `suggested`) leva o selo "sugerida" e o score. Os botões aceitar e rejeitar ficam ali mesmo, inline, e a ação registra quem decidiu. A sugestão de fusão de família (#3) segue o mesmo padrão.
- Aresta pendente de alvo aparece em cinza, com o identificador citado e a nota "não está no corpus". Não é escondida.
- Trecho destacado no texto leva a etiqueta da versão em que ocorreu (#3), para o usuário saber se a evidência é da versão atual ou de uma superada.
- O 👍/👎 por resultado do protótipo entra no TB1 e alimenta `POST /v1/feedback` (plano, linha 130), ligado ao `request_id` da consulta.

O painel de "Critérios de Ranqueamento" com pesos numéricos do protótipo fica de fora do TB1. Os pesos ali são inventados, e um número falso na tela mina a confiança que este Concern quer construir. Se entrar depois, entra com os critérios reais que o #11 e o gabarito da Carolina definirem.

Este Concern fica `partial`: o que está resolvido é a credibilidade das relações e das versões na interface. Como o usuário julga a qualidade do ranking em si (e o que a interface mostra sobre isso) depende do gabarito (#11) e da tarefa concreta do caso (#12).

## Confirmed facts

- Issue #4: arestas explícitas nascem `confirmed` com evidência (`document_version` + localizador); `similar_a` nasce `suggested` com score e só confirma com aceite humano; referência com alvo fora do corpus é aresta pendente, preservada.
- Issue #3: trecho casado carrega `document_version`; sugestão de fusão exige confirmação humana com autoria.
- Protótipo `Busca_Regulatoria_Setor_Eletrico_prototipo.html`: 👍/👎 e "Contestar resultado" por card; link "Fonte oficial"; marcador "Trecho relevante"; painel de transparência com pesos de ranking (similaridade, hierarquia 25%, vigência 15%) e "Alerta de lacuna" quando nenhuma norma passa de 70%.
- Plano, linha 130: `POST /v1/feedback` registra `request_id`, resultado avaliado, relevância e correção ou comentário.

## Decisions

- 2026-09-18 (issue-5): toda aresta mostra origem e estado (explícita com evidência navegável; sugerida com score e aceitar/rejeitar inline; pendente de alvo em cinza com o identificador citado).
- 2026-09-18 (issue-5): confirmação de aresta sugerida e de fusão de família é inline na página do documento, com autoria registrada; sem fila de revisão separada.
- 2026-09-18 (issue-5): 👍/👎 por resultado entra no TB1 via `POST /v1/feedback`.
- 2026-09-18 (issue-5): painel de critérios de ranking com pesos fica fora do TB1.

## Derived requirements and constraints

- A operação que devolve as arestas de um nó inclui, por aresta: tipo, estado (`confirmed` / `suggested` / pendente de alvo), origem, evidência (`document_version` + localizador) quando explícita, score quando `similar_a`, identificador citado quando pendente.
- Aceitar ou rejeitar uma aresta sugerida (e uma fusão de família) é uma operação do backend que grava autor e data; a interface só chama e reflete o novo estado.
- O trecho de evidência de uma aresta é abrível a partir do painel "Relações", chegando à versão e ao localizador certos.
- O 👍/👎 envia `request_id` e o `family_id` avaliado; a interface não pede justificativa obrigatória.

## Open questions

- O que a interface mostra sobre a qualidade do ranking em si (posição no gabarito, "alerta de lacuna" quando nada passa de um limiar): depende do #11 e do #12.
- Quem pode aceitar ou rejeitar arestas e fusões (só a Carolina, qualquer usuário do piloto): depende dos perfis de usuário, ainda em Fog no mapa.

## Evidence

- Map issue #1, Decisions so far (#3 e #4).
- [[d14-data-operations-modeling]], [[i10-hybrid-decision-intelligence]]: estados e evidência das arestas.
- `ideathon/materiais/inspirations/juridico_wallace/Busca_Regulatoria_Setor_Eletrico_prototipo.html`, template descompactado: 👍/👎, "Contestar resultado", "Fonte oficial", painel de transparência.
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md`, linha 130.

## Topic history

- issue-5: fixou que toda aresta e todo trecho mostram origem e estado na interface, confirmação inline com autoria, feedback por resultado no TB1, e deixou o painel de pesos de ranking fora.
