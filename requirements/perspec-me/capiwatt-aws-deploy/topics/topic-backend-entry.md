---
question: Como backend e ai são executados e expostos por HTTPS sem criação de API Gateway e sem ALB/CloudFront (Lambda + Function URL, ECS com IP público, ou outra), e como o ai alcança o Bedrock a partir da AWS?
status: resolved
blocked_by:
  - dw:dw-aws-capability-probe
  - topic-network
claimed_by: s-2026-09-26-aws-arch
concerns:
  - i2-model-serving
  - i9-integration
  - i11-cost
created_at: 2026-09-26
resolved_at: 2026-09-26
---

## Notes

Resolução (Eduardo, 2026-09-26, "aceito as sugestões"): ECS Fargate para backend (0,5 vCPU/1 GB) e `ai` (1 vCPU/2 GB) a partir dos Dockerfiles existentes (`ContainerImage.fromAsset`, publicado pelo image-publishing-role); backend→ai por ECS Service Connect (`AI_BASE_URL=http://ai:8000`); uma distribuição CloudFront com `/v1/*`→ALB e padrão→S3 (OAC), mesma origem; SG do ALB só aceita a prefix list de origem do CloudFront; EFS em `/data/documents` nas duas tasks substitui o volume `documents-data` (Fog "Arquivos compartilhados" resolvido aqui); task role do `ai` com `bedrock:InvokeModel` restrito aos modelos usados, região do Bedrock configurável; tabela DynamoDB da #83 entra no CDK. Lambda rejeitada (Mangum, limite de 15 min, cold start).
