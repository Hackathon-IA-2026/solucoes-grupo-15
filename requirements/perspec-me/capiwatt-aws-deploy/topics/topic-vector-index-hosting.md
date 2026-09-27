---
question: Como o domínio OpenSearch gerenciado na AWS é configurado (versão, instância, k-NN) e populado a cada conta nova, sem reembedding e mantendo o índice como derivado reconstruível?
status: resolved
resolved_at: 2026-09-26
blocked_by: []
claimed_by: s-2026-09-26-vector-index
concerns:
  - i4-storage
  - i2-model-serving
  - i7-reproducibility
created_at: 2026-09-26
---

Issue: https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/90 (sub-issue de #89)

## Notes

Graduado do Fog "Índice vetorial na AWS" em 2026-09-26: Eduardo decidiu que o OpenSearch vai para a AWS (domínio gerenciado na subnet isolada). O estado da busca real (#69/#86) continua como insumo.

Rodada 1 (s-2026-09-26-vector-index, 2026-09-26). Evidência: só `tools/case1_recall/reindex_from_raw_vectors.py` evita o Bedrock; `/index` e `/reindex` re-embedam. O caso 1 tem 352 chunks e custa US$ 0,0043. `embeddings.py` fixa us-east-1 no `REGION` e no `MODEL_VERSION`.
Respostas de Eduardo: "se isso altera o código como está hoje prefiro não"; "carrega só o caso 1"; região do Bedrock: "mantenha o que estiver disponível". Resultado: OpenSearch 2.19 com `nmslib`, `t3.small.search`, 10 GB, só SG; carga pelo seed `/v1/ingestions`; Bedrock segue em us-east-1; nenhuma mudança de código.

Teste do Titan (2026-09-26): responde em us-east-1 e us-west-2 com as credenciais do participante, vetores idênticos — ver evidence/2026-09-26-bedrock-titan-us-east-1.md.

## Synthesis

Resolvido em 2026-09-26 (Eduardo). OpenSearch 2.19 gerenciado, um nó `t3.small.search`, 10 GB gp3, subnet isolada, acesso só por SG, engine `nmslib`; índice populado pelo seed `/v1/ingestions` (re-embeda o caso 1, ~US$ 0,004), só o caso 1 na AWS; recuperação = rodar o seed de novo; Bedrock segue em us-east-1; nenhuma mudança no código do `ai`. Pendente no deploy: confirmar k-NN no `t3.small.search`. Concerns: I4, I2 (substitui a região "configurável, padrão us-west-2" de topic-backend-entry), I7 — todas `partial`.
