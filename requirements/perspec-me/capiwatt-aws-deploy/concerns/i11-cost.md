---
concern_id: i11-cost
concern: ~/.claude/skills/perspec-me/catalog/concerns/i11-cost/README.md
perspective: infrastructure
status: open
topics:
  - topic-network
  - topic-catalog-db-hosting
  - topic-backend-entry
updated_at: 2026-09-26
---

## Current resolution

Custo é critério explícito: o ambiente é de hackathon (72 h) e o time economiza de forma deliberada, com postura de segurança documentada em [[i9-integration]]. Já decidido: sem NAT Gateway, RDS db.t4g.micro em uma única AZ e sem backup. O custo total do M4 ainda não foi estimado (computação, OpenSearch e ALB estão abertos).

## Confirmed facts

- O teto de gasto e os créditos do workshop continuam desconhecidos (Map irmão).

## Decisions

- 2026-09-26 (Eduardo, topic-backend-entry): Fargate backend 0,5 vCPU/1 GB e `ai` 1 vCPU/2 GB (≈ US$ 1,80/dia), ALB (≈ US$ 0,55/dia), CloudFront e EFS marginais.

- 2026-09-26 (Eduardo, topic-network): sem NAT, com tasks em subnet pública para economizar.
- 2026-09-26 (Eduardo, topic-catalog-db-hosting): RDS db.t4g.micro em uma única AZ, sem backup.

## Derived requirements and constraints

- Todo recurso com `RemovalPolicy.DESTROY`; `cdk destroy` ao fim da demonstração.

## Open questions

- Estimativa total depois das decisões de computação e do OpenSearch.

## Evidence

- Preços de referência (us-west-2, sob demanda): NAT Gateway ≈ US$ 0,045/h mais dados; db.t4g.micro ≈ US$ 0,016/h.

## Topic history

- topic-network: sem NAT.
- topic-catalog-db-hosting: RDS mínimo.
