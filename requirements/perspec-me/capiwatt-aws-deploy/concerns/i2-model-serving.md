---
concern_id: i2-model-serving
concern: ~/.claude/skills/perspec-me/catalog/concerns/i2-model-serving/README.md
perspective: infrastructure
status: partial
topics:
  - topic-backend-entry
  - topic-vector-index-hosting
updated_at: 2026-09-26
---

## Current resolution

Na AWS, o `ai` (dono do port `VectorService`, embeddings Bedrock) e o backend rodam como **serviços ECS Fargate** construídos dos Dockerfiles existentes. O `ai` só é alcançável pelo backend via Service Connect (`http://ai:8000`) e chama o Bedrock com uma task role restrita aos modelos usados; a região do Bedrock **fica como está no código hoje (us-east-1, fixada em `ai/app/embeddings.py`)**, chamada a partir da conta em us-west-2 (topic-vector-index-hosting substitui o "configurável, padrão us-west-2" de topic-backend-entry). O acesso público é só pelo CloudFront → ALB → backend. Lambda foi rejeitada: exigiria adaptador (Mangum), tem limite de 15 min que a ingestão/OCR pode estourar e sofre cold start na demonstração.

## Confirmed facts

- Lambda só é viável via CloudFormation (papel próprio com trust lambda); Function URL pública respondeu HTTP 200.
- ALB internet-facing e CloudFront OAC são criáveis via CloudFormation; API Gateway v2 negado na chamada direta (não testado via CloudFormation).
- A política do participante libera Titan Embed V2 explicitamente em us-west-2.
- Titan Embed V2 responde em **us-east-1** e em us-west-2 com as credenciais do participante (1024 dimensões; vetores idênticos, cosseno 1,0000) — nenhum SCP bloqueia us-east-1 (2026-09-26).

## Decisions

- 2026-09-26 (Eduardo, topic-backend-entry): ECS Fargate (backend 0,5 vCPU/1 GB, `ai` 1 vCPU/2 GB), Service Connect, Bedrock por task role; Lambda rejeitada.
- 2026-09-26 (Eduardo, topic-vector-index-hosting): nada no código do `ai` muda para a AWS; o Bedrock segue em us-east-1 com `MODEL_VERSION = amazon.titan-embed-text-v2-us-east-1-1024d-normalized` (nome do índice e do `.jsonl` de vetores brutos inalterados). Substitui a região "configurável, padrão us-west-2" de topic-backend-entry.

## Derived requirements and constraints

- As imagens são publicadas pelo `cdk deploy` (image-publishing-role do bootstrap); `docker push` direto do participante é negado. Docker precisa estar na máquina que faz o deploy.
- A task role do `ai` recebe `bedrock:InvokeModel` só nos ARNs dos modelos usados, além de acesso à tabela DynamoDB da #83 (`DYNAMODB_TABLE_PROCESS_THEMES`).
- ~~`AWS_REGION` do `ai` precisa separar a região do Bedrock da região da conta~~ (superado por topic-vector-index-hosting): o `ai` ignora `AWS_REGION` para o Bedrock; a task role precisa de `bedrock:InvokeModel` no ARN `arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0`.

## Open questions




## Evidence

- [Sondagem de capacidades AWS, 2026-09-26](../evidence/2026-09-26-aws-capability-probe.md) (`dw-aws-capability-probe`).
- [Chamada de teste ao Titan em us-east-1/us-west-2, 2026-09-26](../evidence/2026-09-26-bedrock-titan-us-east-1.md) (topic-vector-index-hosting).

## Topic history

- topic-backend-entry: fixou Fargate + Service Connect + Bedrock por task role.
- topic-vector-index-hosting: Bedrock mantido em us-east-1 sem mudança de código.
- dw-aws-capability-probe: evidência de permissões diretas vs. CloudFormation via bootstrap CDK.
