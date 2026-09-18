---
concern_id: i2-model-serving
concern: ~/.claude/skills/perspec-me/catalog/concerns/i2-model-serving/README.md
perspective: infrastructure
status: partial
topics:
  - issue-2 — Qual é o contrato da interface do serviço vetorial (indexar, buscar, agrupar versões) que isola o Bedrock do resto do backend?
updated_at: 2026-09-18
---

## Current resolution

No primeiro ciclo, o "Bedrock" atrás do port do serviço vetorial ([[i9-integration]]) é **Bedrock somente para embeddings** (modelo de embeddings via Bedrock Runtime API — Titan ou Cohere, escolha na issue #13) **mais um índice vetorial que nós controlamos**. Não se adota Bedrock Knowledge Bases: ele decidiria chunking por nós, tornaria o agrupamento por família um pós-processamento e inviabilizaria rodar a busca localmente. Consumo: o adapter chama o Bedrock apenas para gerar vetores; recuperação e ranking rodam no nosso índice.

Índice vetorial: **OpenSearch** — container local no Compose, OpenSearch Serverless na AWS (decisão de Eduardo, 2026-09-18; pgvector descartado). Como o embedding é servido: o módulo `ai` chama o Bedrock Runtime a partir do adapter `BedrockEmbedder`; o `backend` nunca fala com Bedrock. O que roda local vs. AWS no primeiro ciclo (credenciais, custo) é a issue #8.

## Confirmed facts

- Reunião 2026-09-17: Bedrock para busca vetorial desde o início; o máximo possível roda local.
- Plano (linha 118): "Bedrock fornece as capacidades de modelo"; "vetores de modelos diferentes não devem ser misturados".
- Plano (linha 102): banco vetorial fora da memória temporária das funções.

## Decisions

- 2026-09-18 (issue-2): arranjo (a) — Bedrock para embeddings + índice vetorial próprio; Bedrock Knowledge Bases descartado para o primeiro ciclo.
- 2026-09-18 (issue-2): índice vetorial = OpenSearch (container local / Serverless na AWS).

## Derived requirements and constraints

- O adapter Bedrock implementa só embedding; o índice é outro componente atrás do mesmo port (troca de um não obriga troca do outro).
- `model_version` registra o id do modelo Bedrock usado para os vetores do `corpus_version`.
- Precisa existir um adapter local/fake para o embedding (Demo API sem credenciais AWS, plano linha 98) — mesmo que o embedding "real" nunca rode local.

## Open questions

- Modelo de embeddings concreto — issue #13 (bloqueada pelos documentos da Carolina).

## Evidence

- Map issue #1, Notes.
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 98, 102, 118.

## Topic history

- issue-2: fixou Bedrock-só-embeddings + índice OpenSearch como arranjo do primeiro ciclo; Knowledge Bases e pgvector descartados.
