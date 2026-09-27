---
concern_id: m5-performance-metrics
concern: ~/.claude/skills/perspec-me/catalog/concerns/m5-performance-metrics/README.md
perspective: model
status: resolved
topics:
  - topic-tb1-aws-vs-local
updated_at: 2026-09-27
---

## Current resolution

A métrica de qualidade não muda na AWS. A comparação do M4 reaproveita a resolução do Map irmão ([M5 em capiwatt-lens-hackathon](../../capiwatt-lens-hackathon/concerns/m5-performance-metrics.md)): `Recall@3` por processo agregado, gate `2/3` e meta `3/3`, sobre o corpus `case1-real-v1` e a única pergunta com gabarito. Este Map só acrescenta o critério de equivalência entre a execução na AWS e a baseline local. O gate exige versões iguais, o mesmo conjunto de processos distintos no top 3 e o mesmo `Recall@3`. Ordem e |Δscore| ≤ 0,001 são registrados como informação.

## Confirmed facts

- Baseline local (`hackathon/tools/case1_recall/output/results.json`):
  - top 3 `48500.000639/2019-07`, `48500.000639/2019-07`, `48500.004024/2017-80`, com scores 1,3751, 1,3686 e 1,3638;
  - `Recall@3 = 2/3`, gate aprovado;
  - `model_version` `amazon.titan-embed-text-v2-us-east-1-1024d-normalized`.
- A AWS carrega só o caso 1, pelo mesmo seed, e usa o Bedrock em us-east-1, com vetores idênticos aos locais (topic-vector-index-hosting).

## Decisions

- 2026-09-27 (Eduardo por delegação, topic-tb1-aws-vs-local): a comparação AWS × local entra na Destination deste Map.
- 2026-09-27 (Eduardo por delegação, topic-tb1-aws-vs-local): gate de equivalência = mesmas `corpus_version`/`model_version`/`ranking_version`, mesmo conjunto de processos distintos no top 3 e mesmo `Recall@3` com o gate de M5 aprovado. Ordem idêntica e |Δscore| ≤ 0,001 são só informativos.

## Derived requirements and constraints

- O artefato `hackathon/tools/case1_recall/output/aws_vs_local.json` declara unidade, `k`, denominador, identificadores por posição, scores, versões, `documents_indexed`, `request_id` da AWS, veredito e data.
- Divergência não bloqueia o deploy, mas o M4 só sai com o gate aprovado ou com a divergência explicada no artefato.

## Open questions

- Nenhuma para a Destination atual.

## Evidence

- `hackathon/tools/case1_recall/output/results.json` e `backend_search_envelope_sample.json`.
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md:252` (critério de saída do M4).

## Topic history

- topic-tb1-aws-vs-local: comparação AWS × local incluída na Destination; critério de equivalência definido sobre a métrica do Map irmão.
