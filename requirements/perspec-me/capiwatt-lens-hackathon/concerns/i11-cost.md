---
concern_id: i11-cost
concern: ~/.claude/skills/perspec-me/catalog/concerns/i11-cost/README.md
perspective: infrastructure
status: partial
topics:
  - issue-8 — O que roda local e o que roda na AWS no primeiro ciclo, e como o ambiente local fala com Bedrock e SES (credenciais, custo)?
updated_at: 2026-09-18
---

## Current resolution

No primeiro ciclo o custo AWS é **marginal e não é critério de arquitetura**: a conta é o ambiente temporário do hackathon (AWS Workshop Studio, 72 h — Eduardo, 2026-09-18), e as únicas chamadas remotas são embeddings via Bedrock Runtime (cobrado por token; um corpus de ~100 documentos gera poucos milhares de chunks) e e-mails via SES. Nada é provisionado (sem Lambda, DynamoDB, S3, OpenSearch Serverless), logo nada acumula custo em repouso.

O que ainda falta: (a) confirmar que a conta autoriza invocar o modelo e enviar e-mail — se não, o custo relevante passa a ser o de **não** usar Bedrock/SES (adapters fake como caminho principal); (b) o custo do M4 (implantação), em especial o piso de faturamento do OpenSearch Serverless, que **não** é tratado neste Topic e deve ser avaliado antes de o M4 ser decidido.

## Confirmed facts

- 2026-09-18 (issue-8, diagnóstico `hackathon/scripts/check_aws_capabilities.out`, 23:11 UTC): identidade = role assumida `WSParticipantRole` (credenciais temporárias com session token); `iam:SimulatePrincipalPolicy` negado; conta `542260303569`.
- 2026-09-18 (issue-8, diagnóstico): Bedrock acessível em `us-east-1` e `us-west-2`; `amazon.titan-embed-text-v2:0` e `titan-embed-text-v1` com `authorizationStatus: AUTHORIZED`, agreement e entitlement `AVAILABLE` nas duas regiões; `cohere.embed-multilingual-v3` com `agreementAvailability: NOT_AVAILABLE` (sem acordo de marketplace nesta conta). Também listados `cohere.embed-v4:0` e `amazon.nova-2-multimodal-embeddings-v1:0` (não testados).
- 2026-09-18 (issue-8, diagnóstico): **SES negado em todas as operações de leitura nas duas regiões** (`ses:GetAccount`, `ses:ListEmailIdentities`, `ses:GetSendQuota` — "no identity-based policy allows"); `ses:SendEmail` não foi testado mas nada na política cobre SES.
- 2026-09-18 (issue-8, diagnóstico): CloudWatch Logs, S3 (list), Lambda (list), DynamoDB (list, vazio) e Bedrock AgentCore acessíveis; **OpenSearch Serverless negado** (`aoss:ListCollections`). Existe uma Lambda `BedrockCostTrackerLambda` do workshop — o consumo de Bedrock é monitorado pelo organizador.
- 2026-09-18 (issue-8, Eduardo): conta AWS = ambiente temporário do hackathon (Workshop Studio, 72 h). Nenhuma informação sobre créditos, teto de gasto ou SCPs além do que o Workshop Studio informa.
- Plano (linha 88): F3 mantém o orçamento operacional.
- Página I4 (issue-15): corpus de avaliação da ordem de 100 documentos.

## Decisions

- 2026-09-18 (issue-8): custo não decide nada no primeiro ciclo; nenhum serviço provisionado — a única chamada remota paga é `bedrock:InvokeModel` (Titan V2), monitorada pelo organizador.
- 2026-09-18 (issue-8): sem envio real de e-mail → custo de e-mail zero; Postgres em container → custo zero.

## Derived requirements and constraints

- Toda chamada ao Bedrock Runtime e ao SES deve ser registrada (modelo, tokens, destinatário) para que o consumo do ambiente de 72 h seja auditável — sem isso não há como fechar o custo do TB1.
- A duração de 72 h implica que nada de valor (índice, catálogo, artefatos de avaliação) pode viver só na AWS: a fonte de verdade fica nos volumes locais (coerente com [[i4-storage]]).

## Open questions

- (issue-8, respondida 2026-09-18) Bedrock: Titan V2 autorizado — custo real, marginal, e monitorado pelo organizador (`BedrockCostTrackerLambda`; teto desconhecido). SES: negado — custo SES zero porque o serviço não está disponível; o custo passa a ser o de um provedor alternativo de e-mail, se houver.
- (issue-8) Teto de gasto Bedrock imposto pelo workshop — desconhecido; perguntar ao organizador ou observar o tracker.
- Custo do M4 (OpenSearch Serverless com piso de OCUs, Lambda, API Gateway) — fora deste Topic; a ser levantado quando o M4 for planejado.

## Evidence

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linha 88.
- Informações do AWS Workshop Studio repassadas por Eduardo em 2026-09-18 (issue-8).

## Topic history

- issue-8: criou a página; custo do primeiro ciclo = só invocações Titan V2 na conta temporária (SES indisponível, e-mail sem envio real, Postgres local); custo do M4 deixado explicitamente em aberto.
