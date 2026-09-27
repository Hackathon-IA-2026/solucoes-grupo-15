---
concern_id: i11-cost
concern: ~/.claude/skills/perspec-me/catalog/concerns/i11-cost/README.md
perspective: infrastructure
status: resolved
topics:
  - topic-network
  - topic-catalog-db-hosting
  - topic-backend-entry
  - topic-aws-observability
updated_at: 2026-09-27
---

## Current resolution

Custo é critério explícito: o ambiente é de hackathon (72 h) e o time economiza de forma deliberada, com postura de segurança documentada em [[i9-integration]]. Já decidido: sem NAT Gateway, RDS db.t4g.micro em uma única AZ e sem backup. Com as decisões de computação, OpenSearch e observabilidade, o M4 fica em torno de US$ 4,2/dia, ou cerca de US$ 13 em 72 h. É uma estimativa de ordem de grandeza feita com preços de referência sob demanda, não verificados na conta. O teto de gasto do workshop continua desconhecido. Isso não bloqueia nada, porque tudo sai com `cdk destroy`.

## Confirmed facts

- O teto de gasto e os créditos do workshop continuam desconhecidos (Map irmão).

## Decisions

- 2026-09-26 (Eduardo, topic-backend-entry): Fargate backend 0,5 vCPU/1 GB e `ai` 1 vCPU/2 GB (≈ US$ 1,80/dia), ALB (≈ US$ 0,55/dia), CloudFront e EFS marginais.

- 2026-09-26 (Eduardo, topic-network): sem NAT, com tasks em subnet pública para economizar.
- 2026-09-26 (Eduardo, topic-catalog-db-hosting): RDS db.t4g.micro em uma única AZ, sem backup.

- 2026-09-27 (Eduardo por delegação, topic-aws-observability): observabilidade mínima, com retenção de 3 dias e sem logs de ALB/CloudFront, Container Insights, X-Ray, alarmes ou dashboards.

## Derived requirements and constraints

- Todo recurso com `RemovalPolicy.DESTROY`; `cdk destroy` ao fim da demonstração.

## Open questions

- Nenhuma para a Destination atual (o teto de gasto do workshop segue desconhecido no Map irmão).

## Evidence

- Preços de referência (us-west-2, sob demanda): NAT Gateway ≈ US$ 0,045/h mais dados; db.t4g.micro ≈ US$ 0,016/h.

- Estimativa por dia (2026-09-27, preços de referência):
  - Fargate: 1,80
  - ALB: 0,55
  - RDS db.t4g.micro com 20 GB: ≈ 0,46
  - OpenSearch `t3.small.search` (≈ US$ 0,036/h) com 10 GB gp3: ≈ 0,90
  - 4 IPv4 públicos (2 do ALB e 2 das tasks, US$ 0,005/h cada): ≈ 0,48
  - Marginais: CloudWatch Logs (< 0,1 GB ingerido), EFS, S3, CloudFront, Cognito, DynamoDB sob demanda e Bedrock (≈ 0,004 por seed).

## Topic history

- topic-network: sem NAT.
- topic-catalog-db-hosting: RDS mínimo.
- topic-backend-entry: dimensionamento das tasks Fargate e ALB.
- topic-aws-observability: observabilidade mínima e fechamento da estimativa total (≈ US$ 13 em 72 h).
