# Resultados medidos e limites

## Recuperação no caso 1

A consulta de Carolina sobre fiscalização de conexões de MMGD foi avaliada no corpus controlado de **10 documentos**. O [gabarito](../hackathon/data/case-1-carolina-mmgd/README.md) contém três processos; a métrica é Recall@3 sobre **processos distintos agregados**, não sobre três chunks ou três PDFs ([definição M5](../requirements/perspec-me/capiwatt-lens-hackathon/concerns/m5-performance-metrics.md)).

| Artefato | Resultado registrado |
| --- | --- |
| [Medição pelo serviço `ai`](../hackathon/tools/case1_recall/output/results.json) | `after_index.recall_at_3 = 0,6666666666666666` (2/3); 10 documentos indexados; processos `48500.000639/2019-07` e `48500.004024/2017-80` recuperados entre os três primeiros distintos. O terceiro processo do gabarito, `48500.901433/2024-53`, não foi recuperado nesse Top 3. |
| [Protótipo de baseline](../hackathon/tools/prototypes/recall_baseline/output/results.json) | `recall_at_3 = 0,6666666666666666` (2/3) no mesmo gabarito. |

O gate definido em M5 é 2/3; a meta desejada é 3/3. O [resultado do serviço](../hackathon/tools/case1_recall/output/results.json) também registra 2/3 após reindexação pelo `ai` e a partir dos vetores brutos. Ele não prova desempenho em consultas novas, no corpus completo nem em tráfego de produção. O valor `estimated_embedding_cost_usd` desse JSON é estimativa de **embeddings dessa medição**, não custo de operação da stack.

## Como reproduzir

O [script de ingestão e medição](../hackathon/tools/case1_recall/seed_and_measure.py) e a [suíte ponta a ponta](../hackathon/tests_e2e/README.md) documentam os comandos e pré-requisitos. A suíte usa vetores pré-computados fora do Git; sem eles, é pulada. A [execução local padrão](../README.md#como-rodar-o-projeto) usa fixtures e `EMBEDDER=fake`, então não reproduz o Recall@3 real apenas com `docker compose up`.

## Limitações para uma avaliação de piloto

- A [URL da demo AWS](../README.md#demo) não é estável neste repositório; disponibilidade atual não foi aferida aqui.
- O [corpus completo](../hackathon/data/processos%20aneel/README.md) tem manifestos versionados, mas os documentos originais grandes ficam fora do Git. A medição acima cobre só o caso 1.
- Não há medição publicada de latência, robustez de consultas variadas, precisão com negativos representativos nem custo total da implantação; a [Concern I11](../requirements/perspec-me/capiwatt-aws-deploy/concerns/i11-cost.md) contém decisões e estimativas parciais, não uma fatura observada.
- O [login local](../hackathon/frontend/src/pages/LoginPage.tsx) é demonstrativo; [Cognito](../hackathon/backend/app/auth.py) é uma opção do backend. A [revisão de segurança](security.md) registra lacunas, sem alegar conformidade.
