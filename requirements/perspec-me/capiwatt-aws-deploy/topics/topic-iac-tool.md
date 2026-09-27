---
question: Terraform (preferência) ou CDK em Python (plano B) provisiona a infraestrutura na conta do hackathon, e onde fica o estado do IaC dado que a conta dura 72 h?
status: resolved
blocked_by:
  - dw:dw-aws-capability-probe
claimed_by: s-2026-09-26-aws-arch
concerns:
  - i8-maintainability
  - i7-reproducibility
created_at: 2026-09-26
resolved_at: 2026-09-26
---

## Notes

Eduardo (2026-09-26): preferência por Terraform; se a sondagem mostrar que o WSParticipantRole não cria recursos por chamada direta de API, o plano B é CDK em Python.

Resolução (Eduardo, 2026-09-26, "aceito as sugestões"): CDK em Python para toda a infraestrutura, região us-west-2 (bootstrap existente), app em `hackathon/infra/` com um stack por grupo (rede, dados, computação, frontend, autenticação), deploy da máquina do time com `.env` assumindo o `deploy-role`. Terraform abandonado.
