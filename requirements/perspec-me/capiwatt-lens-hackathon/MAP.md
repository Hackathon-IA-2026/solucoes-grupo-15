# CapiWatt Lens — Caso 1 (Carolina) — Map

**Backend:** tracker — Wayfinder map: [CapiWatt Lens — Caso 1 (Carolina): mapa de decisões](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/1)

Destination confirmed by Eduardo on 2026-09-18 (revision 2, after the 2026-09-17 meeting decisions). Seed: `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md`.

## Perspective resolution

_Counts are of Concerns touched under this Map, by current `status` on their Resolution page. Last refreshed 2026-09-26 (issue #28 resolved into I9, U4 e I4 — todas permanecem `partial`; sessão de verificação registrou em I2 a permissão de geração no Bedrock e a postura de exposição da #39; M1 e D14 permanecem `partial` — sessão de continuação da issue #13 travou o modelo em Titan V2, adiou a medição de `Recall@3`, fechou a #56 e introduziu extração por IA antes do chunking; abriu a issue #57 (D1/U4); em seguida, a issue #64 removeu o agrupamento por família **da visualização** — busca sem card único por família nem dedup, card por chunk casado, sem indicador de versão relacionada — mantendo `family_id`/`reassign_family` intactos como dado de backend e no contrato do port; unidade de paginação da busca (I9) muda de família para chunk; D4, D11, U4 e I9 permanecem `partial` (novas questões abertas: campo de desempate em I9, destino da confirmação de fusão em U4); contagens inalteradas porque nenhum Concern trocou de status nesta rodada; em 2026-09-27, a issue #95 alinhou `index` à implementação: entrada = Markdown já extraído inline, extração no pipeline #59/#68 antes da fronteira. Isso revisou I9 e I4, que permanecem `partial`, sem mudar as contagens)._

| Perspective | unexamined | open | partial | resolved | deferred | not-applicable | superseded | Perspective page |
|---|---|---|---|---|---|---|---|---|
| O — System Objectives | 0 | 0 | 0 | 3 | 0 | 0 | 0 | _(none yet)_ |
| U — User Experience | 0 | 0 | 4 | 1 | 0 | 0 | 0 | _(none yet)_ |
| I — Infrastructure | 0 | 0 | 7 | 1 | 0 | 0 | 0 | _(none yet)_ |
| M — Model | 0 | 0 | 1 | 2 | 0 | 0 | 0 | _(none yet)_ |
| D — Data | 0 | 0 | 3 | 3 | 0 | 0 | 0 | _(none yet)_ |

## Links

- Autoridade de disponibilidade AWS: [Ambiente AWS — serviços disponíveis](../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md), confirmada por Eduardo em 2026-09-20. Revisão das issues #7/#8 preserva o corte local; I2, I6, I7, I9 e I11 foram atualizadas sem alterar seus estados nem as contagens acima. Diagnósticos anteriores são evidência histórica; o inventário prevalece em divergências de disponibilidade.

- Wayfinder map issue: [CapiWatt Lens — Caso 1 (Carolina): mapa de decisões](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/1) — Destination, Notes, Decisions so far, Fog (Not yet specified), and Out of scope live there, not here.
- Topics: child issues of the map issue carrying `resolver: perspec-me`; Frontier = open, unblocked, unassigned children (live `gh` query, never a local list).
- Delivery gate: [Carolina entrega o caso 1: detalhamento, documentos e gabarito de priorização](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/14) (`wayfinder:task`) — blocks the four case-dependent Topics via native issue dependencies.
- Concern Resolution pages: [concerns/](concerns/) (created on first touch)
- Perspective pages: [perspectives/](perspectives/) (created on demand)
