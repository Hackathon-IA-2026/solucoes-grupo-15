---
concern_id: i8-maintainability
concern: ~/.claude/skills/perspec-me/catalog/concerns/i8-maintainability/README.md
perspective: infrastructure
status: partial
topics:
  - topic-iac-tool
updated_at: 2026-09-26
---

## Current resolution

Toda a infraestrutura AWS é código **CDK em Python** em `hackathon/infra/`, implantado em **us-west-2** sobre o bootstrap CDK que o workshop já provê. Um stack por grupo de recursos (rede, dados, computação, frontend, autenticação), para que cada Topic seguinte vire um stack isolado. Terraform foi descartado porque, com as credenciais do participante, não cria nem lê rede.

## Confirmed facts

- Terraform com WSParticipantRole: S3 e Cognito ok; qualquer recurso de rede falha (até ler a VPC padrão).
- CloudFormation com o cfn-exec-role do bootstrap CDK (us-west-2, AdministratorAccess) cria VPC, SG, RDS, ALB, Lambda e ECS com papéis.
- A conta do workshop muda entre sessões (ID diferente do de 2026-09-18); o IaC precisa recriar tudo numa conta nova.

## Decisions

- 2026-09-26 (Eduardo, topic-iac-tool): CDK em Python, us-west-2, `hackathon/infra/`, um stack por grupo; Terraform abandonado.

## Derived requirements and constraints

- O deploy assume `cdk-hnb659fds-deploy-role-<conta>-us-west-2` a partir das credenciais de `.env`; o CloudFormation executa com o `cfn-exec-role`. Nenhum recurso é criado por chamada direta.
- Nada é hardcoded por conta: o ID muda entre sessões do workshop.
- Deploy a partir da máquina do time; o Code Editor do workshop não é caminho suportado (identidade não testada).

## Open questions

- Se o workshop entregar uma conta nova sem bootstrap em us-west-2, rodar `cdk bootstrap` com credenciais do participante (não testado).

## Evidence

- [Sondagem de capacidades AWS, 2026-09-26](../evidence/2026-09-26-aws-capability-probe.md) (`dw-aws-capability-probe`).

## Topic history

- topic-iac-tool: fixou CDK Python em us-west-2, layout por stack e modo de deploy.
- dw-aws-capability-probe: evidência de permissões diretas vs. CloudFormation via bootstrap CDK.
