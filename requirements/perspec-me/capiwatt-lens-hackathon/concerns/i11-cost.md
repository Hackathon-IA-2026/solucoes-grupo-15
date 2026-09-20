---
concern_id: i11-cost
concern: ~/.claude/skills/perspec-me/catalog/concerns/i11-cost/README.md
perspective: infrastructure
status: partial
topics:
  - issue-8 — O que roda local e o que roda na AWS no primeiro ciclo, e como o ambiente local fala com Bedrock e SES (credenciais, custo)?
updated_at: 2026-09-20
---

## Current resolution

**Autoridade de disponibilidade (Eduardo, 2026-09-20):** [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md) prevalece sobre hipóteses do plano e diagnósticos anteriores quanto a serviços, regiões e permissões. Diagnósticos datados permanecem evidência histórica; disponibilidade não equivale à validação funcional do fluxo da aplicação.

No primeiro ciclo, mantido por Eduardo em 2026-09-20, não são provisionados recursos AWS do produto. O consumo AWS previsto é somente o das invocações de embeddings; não há envio real de e-mail. Postgres, OpenSearch e arquivos ficam locais. Isso não significa custo total zero nem gratuidade dos serviços disponíveis.

O teto/créditos do workshop e o orçamento de implantação posterior permanecem desconhecidos. A identificação anterior de `BedrockCostTrackerLambda` é evidência histórica de monitoramento do organizador, não garantia de cobertura nem de limite de gasto. Registrar as invocações do produto. A arquitetura e o custo do M4 devem partir do inventário, sem pressupor nova API Gateway ou OpenSearch Serverless.

## Confirmed facts

- 2026-09-20 (Eduardo): confirmou o corte local proposto e determinou que o documento AWS é a autoridade para disponibilidade de serviços. Os diagnósticos de 2026-09-18 abaixo são históricos.

- 2026-09-18 (issue-8, diagnóstico `hackathon/scripts/check_aws_capabilities.out`, 23:11 UTC): identidade = role assumida `WSParticipantRole` (credenciais temporárias com session token); `iam:SimulatePrincipalPolicy` negado; conta `542260303569`.
- 2026-09-18 (issue-8, diagnóstico): Bedrock acessível em `us-east-1` e `us-west-2`; `amazon.titan-embed-text-v2:0` e `titan-embed-text-v1` com `authorizationStatus: AUTHORIZED`, agreement e entitlement `AVAILABLE` nas duas regiões; `cohere.embed-multilingual-v3` com `agreementAvailability: NOT_AVAILABLE` (sem acordo de marketplace nesta conta). Também listados `cohere.embed-v4:0` e `amazon.nova-2-multimodal-embeddings-v1:0` (não testados).
- 2026-09-18 (issue-8, diagnóstico): **SES negado em todas as operações de leitura nas duas regiões** (`ses:GetAccount`, `ses:ListEmailIdentities`, `ses:GetSendQuota` — "no identity-based policy allows"); `ses:SendEmail` não foi testado mas nada na política cobre SES.
- 2026-09-18 (issue-8, diagnóstico): CloudWatch Logs, S3 (list), Lambda (list), DynamoDB (list, vazio) e Bedrock AgentCore acessíveis; **OpenSearch Serverless negado** (`aoss:ListCollections`). Existe uma Lambda `BedrockCostTrackerLambda` do workshop — o consumo de Bedrock é monitorado pelo organizador.
- 2026-09-18 (issue-8, Eduardo): conta AWS = ambiente temporário do hackathon (Workshop Studio, 72 h). Nenhuma informação sobre créditos, teto de gasto ou SCPs além do que o Workshop Studio informa.
- Plano (linha 88): F3 mantém o orçamento operacional.
- Página I4 (issue-15): corpus de avaliação da ordem de 100 documentos.

## Decisions

- 2026-09-20 (issue-8, Eduardo): disponibilidade de outros serviços não muda o corte local nem cria novas despesas planejadas; custos de implantação continuam fora do primeiro ciclo.

- 2026-09-18 (issue-8): custo não decide nada no primeiro ciclo; nenhum serviço provisionado — a única chamada remota paga é `bedrock:InvokeModel` (Titan V2), monitorada pelo organizador.
- 2026-09-18 (issue-8): sem envio real de e-mail → custo de e-mail zero; Postgres em container → custo zero.

## Derived requirements and constraints

- Disponibilidade no documento não informa preço, créditos ou teto. Não tratar serviços disponíveis como gratuitos.

- Registrar modelo e consumo das chamadas ao Bedrock Runtime para auditoria do TB1. Auditoria de provedor de e-mail só se aplica quando houver envio real, fora deste ciclo.
- A duração de 72 h implica que nada de valor (índice, catálogo, artefatos de avaliação) pode viver só na AWS: a fonte de verdade fica nos volumes locais (coerente com [[i4-storage]]).

## Open questions

- Hipótese de consumo do primeiro ciclo: apenas embeddings; depende de manter o corte local. Teto do workshop e custo de implantação posterior seguem em aberto.

- (issue-8, respondida 2026-09-18) Bedrock: Titan V2 autorizado — custo real, marginal, e monitorado pelo organizador (`BedrockCostTrackerLambda`; teto desconhecido). SES: negado — custo SES zero porque o serviço não está disponível; o custo passa a ser o de um provedor alternativo de e-mail, se houver.
- (issue-8) Teto de gasto Bedrock imposto pelo workshop — desconhecido; perguntar ao organizador ou observar o tracker.
- Custo do M4 — fora deste Topic; levantar sobre uma arquitetura compatível com o inventário quando a implantação for planejada.

## Evidence

- [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md), lido em 2026-09-20.
- Eduardo, 2026-09-20: “vamos seguir as sugestões” e “trate esse documento como autoridade para disponibilidade de serviços aws”.

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linha 88.
- Informações do AWS Workshop Studio repassadas por Eduardo em 2026-09-18 (issue-8).

## Topic history

- issue-8 (2026-09-20): revisão de disponibilidade aceita por Eduardo; inventário AWS incorporado como autoridade, corte local preservado. Mantidas as demais decisões desta página.

- issue-8: criou a página; custo do primeiro ciclo = só invocações Titan V2 na conta temporária (SES indisponível, e-mail sem envio real, Postgres local); custo do M4 deixado explicitamente em aberto.
