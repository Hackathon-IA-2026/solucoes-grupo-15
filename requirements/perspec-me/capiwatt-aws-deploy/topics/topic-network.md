---
question: Em que rede os componentes rodam (VPC padrão vs. VPC própria) e como Postgres e OpenSearch ficam inacessíveis pela internet, dado que o EC2 só permite consultar VPCs e subnets?
status: resolved
blocked_by:
  - dw:dw-aws-capability-probe
claimed_by: s-2026-09-26-aws-arch
concerns:
  - i4-storage
  - i9-integration
created_at: 2026-09-26
resolved_at: 2026-09-26
---

## Notes

Pedido original: "criar uma VPC se necessário para o banco de dados". O inventário sugere que criar VPC/SG é negado — a sondagem confirma.

Resolução (Eduardo, 2026-09-26): VPC própria via CDK, 2 AZs, subnets públicas (ALB + tasks com IP público só para saída) e privadas isoladas (RDS, OpenSearch), sem NAT, security groups encadeados; acesso administrativo via SSM Session Manager; OpenSearch vai para a AWS. A economia de segurança é deliberada e está documentada em concerns/i9-integration.md.
