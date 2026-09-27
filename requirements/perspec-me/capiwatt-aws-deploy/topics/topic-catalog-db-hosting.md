---
question: Onde roda o Postgres do catálogo sem RDS/Aurora no inventário (ECS Fargate + EFS ou outra opção), e como schema e dados de demonstração chegam a ele?
status: resolved
blocked_by:
  - dw:dw-aws-capability-probe
  - topic-network
claimed_by: s-2026-09-26-aws-arch
concerns:
  - i4-storage
  - i7-reproducibility
  - i11-cost
created_at: 2026-09-26
resolved_at: 2026-09-26
---

## Notes

Resolução (Eduardo, 2026-09-26, "aceito as sugestões"): RDS Postgres 16 db.t4g.micro, uma AZ, sem backup, senha gerenciada pelo RDS; `config.py` monta a `DATABASE_URL` de `DB_HOST`/`DB_USER`/`DB_PASSWORD`; schema via `create_all`; seed via `POST /v1/ingestions` pós-deploy (sem dump do local); SSM = ECS Exec com port forwarding a partir da task do backend.
