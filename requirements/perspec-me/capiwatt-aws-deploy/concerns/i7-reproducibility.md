---
concern_id: i7-reproducibility
concern: ~/.claude/skills/perspec-me/catalog/concerns/i7-reproducibility/README.md
perspective: infrastructure
status: partial
topics:
  - topic-iac-tool
  - topic-catalog-db-hosting
  - topic-vector-index-hosting
  - topic-tb1-aws-vs-local
updated_at: 2026-09-27
---

## Current resolution

O ambiente AWS é reproduzível a partir do git: o estado do IaC vive nos stacks CloudFormation da própria conta, sem arquivo de estado para guardar, e a conta do workshop é descartável (72 h, ID muda entre sessões). Recriar = `cdk deploy` numa conta nova. A reprodutibilidade de buscas (Map irmão, #9: embeddings preservados, replay offline) não muda por a implantação estar em us-west-2.

A reprodução do TB1 na AWS (topic-tb1-aws-vs-local) é verificada contra a baseline local commitada. O gate exige as mesmas versões, o mesmo conjunto de processos no top 3 e o mesmo `Recall@3`; ordem e scores são só informativos. A comparação real só acontece no deploy.

## Confirmed facts

- A conta do workshop em 2026-09-26 tem ID diferente da de 2026-09-18.
- Titan Embed V2 é liberado explicitamente em us-west-2 na política do participante.

## Decisions

- 2026-09-26 (Eduardo, topic-catalog-db-hosting): cada conta nova = `cdk deploy`, depois `seed.sh` (`POST /v1/ingestions`); schema por `create_all`; dados de interação do local não migram.

- 2026-09-26 (Eduardo, topic-iac-tool): sem backend de estado remoto; a fonte de verdade é o código CDK em `hackathon/infra/`.
- 2026-09-26 (Eduardo, topic-vector-index-hosting): o índice de cada conta nova é refeito pelo seed (`/v1/ingestions` re-embeda via Bedrock, ~US$ 0,004 para o caso 1); não se copiam vetores brutos entre contas. Recuperação dentro da conta = rodar o seed de novo. Os vetores brutos gerados na AWS ficam no EFS (`/data/documents/_raw_vectors/`), mantendo o índice como derivado.

- 2026-09-27 (Eduardo por delegação, topic-tb1-aws-vs-local): a baseline local é o `results.json` commitado, sem reexecução local. O lado AWS roda pela API pública e grava `output/aws_vs_local.json` com o `request_id` da AWS.

## Derived requirements and constraints

- Nenhum dado de valor vive só na AWS; dados de demonstração precisam de um passo de carga repetível após cada deploy (detalhe em topic-catalog-db-hosting).
- Mesmo modelo nas duas regiões (cosseno 1,0000 no teste de 2026-09-26), então o índice re-embedado na AWS é equivalente ao local; ainda assim, não é bit a bit o das medições de recall do #73 (vetores re-embedados); paridade exata não é requisito.
- `tools/case1_recall/reindex_from_raw_vectors.py` não está na imagem do `ai`; na AWS ele não é o caminho de recuperação.

## Open questions

- Resultado real da comparação AWS × local, que só existe depois do deploy (topic-tb1-aws-vs-local).

## Evidence

- [Chamada de teste ao Titan em us-east-1/us-west-2, 2026-09-26](../evidence/2026-09-26-bedrock-titan-us-east-1.md); custo real do caso 1 em `hackathon/tools/case1_recall/output/results.json` (US$ 0,0043).
- [Sondagem de capacidades AWS, 2026-09-26](../evidence/2026-09-26-aws-capability-probe.md).
- `hackathon/tools/case1_recall/output/results.json`: index, reindex via `ai` e reindex a partir dos vetores brutos dão o mesmo top 3 e os mesmos scores.

## Topic history

- topic-catalog-db-hosting: carga repetível pós-deploy.
- topic-vector-index-hosting: índice refeito pelo seed em cada conta; sem cópia de vetores.
- topic-iac-tool: fixou estado do IaC = stacks CloudFormation, recriação por deploy.
- topic-tb1-aws-vs-local: critério de equivalência da reprodução na AWS contra a baseline local (gate por conjunto de processos e `Recall@3`, não bit a bit).
