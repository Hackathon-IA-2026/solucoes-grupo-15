---
question: A comparação do TB1 repetido na AWS com a avaliação local (critério de saída do M4) entra na Destination deste Map — e, se entrar, quais métricas, qual corpus e qual critério de equivalência são comparados?
status: resolved
resolved_at: 2026-09-27
blocked_by: []
claimed_by: s-2026-09-27-issues-99-100
concerns:
  - m5-performance-metrics
  - i7-reproducibility
created_at: 2026-09-26
---

Issue: https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/100 (sub-issue de #89)

## Notes

Saiu do Fog "Comparação TB1 AWS × local" (O/M) em 2026-09-26, a pedido de Eduardo. O plano de execução (`hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md:252`) define o critério de saída do M4 como "TB1 repetido na AWS e resultados comparados à avaliação local". A Destination confirmada deste Map não cita a comparação, então a primeira decisão é se ela entra (e a Destination muda) ou vai para Out of scope.

Evidência relevante: o topic-vector-index-hosting carrega só o caso 1 na AWS e mantém o Bedrock em us-east-1.

Evidência levantada (s-2026-09-27-issues-99-100):

- A avaliação local é `hackathon/tools/case1_recall/output/results.json`: corpus `case1-real-v1` (10 documentos, 342 chunks), uma pergunta com gabarito de três processos e `top_k=3`.
  - As três rotas de indexação (index, reindex via `ai` e reindex a partir dos vetores brutos) dão o mesmo top 3: `48500.000639/2019-07` (duas vezes) e `48500.004024/2017-80`.
  - Scores: 1,3751, 1,3686 e 1,3638.
  - `Recall@3 = 2/3`, gate aprovado.
- A métrica e o gate vêm do Map irmão ([M5](../../capiwatt-lens-hackathon/concerns/m5-performance-metrics.md)): `Recall@3` por processo agregado, gate `2/3`, meta `3/3`.
- O envelope público de `POST /v1/search` já traz `request_id`, `corpus_version`, `model_version` e `ranking_version` (`output/backend_search_envelope_sample.json`).
- O Titan devolve vetores idênticos em us-east-1 e us-west-2 (cosseno 1,0000, evidence/2026-09-26-bedrock-titan-us-east-1.md).
- A suíte e2e da #88 (branch `feat/e2e-caso1-issues-88-92-98`) já mede `Recall@3` por HTTP sobre as rotas `/v1/*`.

Decisão (Eduardo, 2026-09-27, por delegação: "resolva as issues #99 e #100 com as recomendações indicadas pelo agente"): recomendação do agente aceita sem alteração.

## Synthesis

Resolvido em 2026-09-27.

- **Destination.** A comparação entra na Destination, porque é o critério de saída do M4 no plano e custa pouco: a baseline local já está commitada e o envelope já traz as versões.
- **Corpus e pergunta.** Só o caso 1 (`case1-real-v1`, o mesmo carregado na AWS pelo seed) e só a pergunta com gabarito de `results.json`.
- **Baseline.** O `results.json` commitado. O lado local não é reexecutado.
- **Execução na AWS.** Um script envia `POST /v1/search` à URL pública do CloudFront com `top_k=3` e o access token de uma conta de demo (`equipe`), obtido pelo app client de operação do `seed.sh`. Nada acessa RDS nem OpenSearch direto.
- **Métricas registradas.**
  - Os identificadores por posição: `document_version` e processo agregado.
  - Os scores.
  - `Recall@3` por processo agregado (unidade, `k` e denominador declarados, conforme M5).
  - `corpus_version`, `model_version`, `ranking_version`, `documents_indexed` e o `request_id` da AWS.
- **Critério de equivalência (gate).** Todos estes precisam valer ao mesmo tempo:
  - `corpus_version`, `model_version` e `ranking_version` iguais aos da baseline;
  - o mesmo conjunto de processos distintos no top 3;
  - o mesmo `Recall@3` (2/3) e o gate de M5 aprovado.
- **Informativo, fora do gate.**
  - Ordem idêntica dos hits.
  - |Δscore| ≤ 0,001 por posição. O HNSW é aproximado e os scores 2 e 3 estão a 0,005 um do outro, então uma troca de ordem entre eles não reprova. Paridade bit a bit não é requisito ([I7](../concerns/i7-reproducibility.md)).
- **Artefato.** `hackathon/tools/case1_recall/output/aws_vs_local.json`, commitado, com os dois lados, o veredito e a data. O `request_id` da AWS liga o artefato à linha `SearchExecution` e ao log da requisição (topic-aws-observability).
- **Divergência.** Um resultado divergente vira achado registrado, depurado pelo `request_id`/replay. Não bloqueia o deploy, mas o M4 só sai com o gate aprovado ou com a divergência explicada.

Concerns: [M5](../concerns/m5-performance-metrics.md) `resolved` (neste Map), [I7](../concerns/i7-reproducibility.md) `partial` (a comparação real só acontece no deploy). Contratos de fronteira inalterados.
