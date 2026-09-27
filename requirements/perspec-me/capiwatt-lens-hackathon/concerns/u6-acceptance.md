---
concern_id: u6-acceptance
concern: ~/.claude/skills/perspec-me/catalog/concerns/u6-acceptance/README.md
perspective: user-experience
status: partial
topics:
  - issue-5 — Como a interface expõe a exploração do grafo de relações e o objeto-documento com versões, a partir dos protótipos juridico_referencia?
  - issue-94 — Que chave o 👍/👎 da interface envia, agora que o backend exige o chunk avaliado (#82)?
  - issue-93 — Como as telas consomem a busca plana por chunk (sem face/matched_chunks), com paginação por cursor?
updated_at: 2026-09-27
---

## Current resolution

O usuário aceita o grafo e a busca porque cada relação e cada trecho mostram de onde vieram (decisão de Eduardo, 2026-09-18). Uma regra só, aplicada em todo lugar:

- Aresta explícita (`origin: explicit`, estado `confirmed`) leva o selo "explícita". Ao clicar, a interface abre o trecho da versão e o localizador onde a referência foi encontrada, e o usuário pode ir até ele.
- Aresta `similar_a` (estado `suggested`) leva o selo "sugerida" e o score. Os botões aceitar e rejeitar ficam ali mesmo, inline, e a ação registra quem decidiu. A sugestão de fusão de família (#3) segue o mesmo padrão.
- Aresta pendente de alvo aparece em cinza, com o identificador citado e a nota "não está no corpus". Não é escondida.
- Trecho destacado no texto leva a etiqueta da versão em que ocorreu (#3), para o usuário saber se a evidência é da versão atual ou de uma superada.
- O 👍/👎 por resultado do protótipo entra no TB1 e alimenta `POST /v1/feedback` (plano, linha 130), ligado ao `request_id` da consulta.

**Revisão (issue-94, 2026-09-27): o voto identifica o chunk avaliado.** Desde a #82 o backend exige, além do `request_id`, a chave do chunk: `document_version` + `chunk_index` (índice real do chunk no documento, estável desde a #96 — [[i9-integration]]). A suíte e2e da #88 mostrou que a interface ainda enviava `{request_id, family_id, vote}` e recebia 422. Agora a interface envia `{request_id, document_version, chunk_index, vote}`, sem `family_id` (que o backend só aceita como opcional, por compatibilidade). Enquanto as telas ainda consomem a busca agrupada (`face`/`matched_chunks`, divergência aberta na #93), um card pode reunir vários chunks; o voto do card é registrado no **chunk de maior score** do card — o que determina a posição e a aderência mostradas (empate: o primeiro da lista). Quando a #93 tornar cada card um chunk, o alvo do voto passa a ser o próprio resultado.

**Revisão (issue-93, 2026-09-27): o voto sai direto do resultado.** As telas passaram a consumir o envelope plano por chunk ([[u4-visualization]]), e a escolha do "chunk de maior score do card" deixou de existir. Na tela de consulta (`/consulta-api`, `SearchPage`), cada card é um chunk e o 👍/👎 do card envia o `document_version` + `chunk_index` do próprio resultado. Na `ExplorePage` (`/explorar`), que ranqueia **processos**, o card reúne os trechos de um mesmo processo SEI. O voto desse card vai para o trecho mais bem ranqueado do processo, que é o **primeiro na ordem do backend**, com a chave lida desse resultado. Não há mais cálculo de score no frontend.

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
- 2026-09-27 (issue-93): o alvo do voto é o próprio resultado por chunk (`SearchPage`); no card por processo da `ExplorePage`, é o primeiro trecho do processo na ordem do backend. Supersede a escolha "chunk de maior score do card" da issue-94.
- 2026-09-27 (issue-94): o 👍/👎 envia a chave por chunk (`request_id`, `document_version`, `chunk_index`, `vote`), igual ao contrato do backend desde a #82; `family_id` não é mais enviado.

## Derived requirements and constraints

- A operação que devolve as arestas de um nó inclui, por aresta: tipo, estado (`confirmed` / `suggested` / pendente de alvo), origem, evidência (`document_version` + localizador) quando explícita, score quando `similar_a`, identificador citado quando pendente.
- Aceitar ou rejeitar uma aresta sugerida (e uma fusão de família) é uma operação do backend que grava autor e data; a interface só chama e reflete o novo estado.
- O trecho de evidência de uma aresta é abrível a partir do painel "Relações", chegando à versão e ao localizador certos.
- ~~O 👍/👎 envia `request_id` e o `family_id` avaliado~~ **Superado pela issue-94:** o 👍/👎 envia `request_id` + `document_version` + `chunk_index` do chunk avaliado; a interface não pede justificativa obrigatória.

## Open questions

- O que a interface mostra sobre a qualidade do ranking em si (posição no gabarito, "alerta de lacuna" quando nada passa de um limiar): depende do #11 e do #12.
- Quem pode aceitar ou rejeitar arestas e fusões, **quando existirem pessoas distintas** (só a Carolina, qualquer usuário do piloto): depende dos perfis de usuário, ainda em Fog no mapa. Isto **não contradiz** [[d4-data-dictionary]]: lá está a regra de curadoria pretendida ("qualquer usuário autenticado, com autoria registrada"); aqui está o que falta para aplicá-la a pessoas reais. No TB1 não há autenticação, e o autor registrado é o usuário demo único (2026-09-25).

- ~~(issue-94, pendente de confirmação do Eduardo) Num card agrupado com vários chunks, o voto vai para o chunk de maior score.~~ **Resolvido pela issue-93** para a `SearchPage` (cada card é um chunk).
- (issue-93, pendente de confirmação do Eduardo) Na `ExplorePage` o card continua sendo um processo, com vários trechos, e o voto vai para o primeiro trecho do processo. A alternativa é um 👍/👎 por trecho na lista "Motivos do ranking". A escolha foi a mais conservadora: sem mudar o layout do ranking por processo.

## Evidence

- Map issue #1, Decisions so far (#3 e #4).
- [[d14-data-operations-modeling]], [[i10-hybrid-decision-intelligence]]: estados e evidência das arestas.
- `ideathon/materiais/inspirations/juridico_referencia/Busca_Regulatoria_Setor_Eletrico_prototipo.html`, template descompactado: 👍/👎, "Contestar resultado", "Fonte oficial", painel de transparência.
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md`, linha 130.
- issue-93: `hackathon/frontend/src/pages/SearchPage.tsx` (voto por card = chunk), `hackathon/frontend/src/services/appRepository.ts::mapSearchEnvelope` (`feedbackChunk` = primeiro trecho do processo), `SearchPage.test.tsx`/`ExplorePage.test.tsx`.
- issue-94: `hackathon/frontend/src/api/feedback.ts`, `hackathon/backend/app/routes/feedback.py` (`FeedbackIn`), `hackathon/tests_e2e/test_case1_e2e.py::test_frontend_feedback_payload_is_accepted`.

## Topic history

- issue-5: fixou que toda aresta e todo trecho mostram origem e estado na interface, confirmação inline com autoria, feedback por resultado no TB1, e deixou o painel de pesos de ranking fora.
- issue-94: o 👍/👎 passou a enviar a chave por chunk (`document_version` + `chunk_index`) no lugar do `family_id`; num card agrupado, o voto vai para o chunk de maior score até a #93.
- issue-93: o voto passou a sair direto do resultado por chunk; na `ExplorePage`, do primeiro trecho do processo.
