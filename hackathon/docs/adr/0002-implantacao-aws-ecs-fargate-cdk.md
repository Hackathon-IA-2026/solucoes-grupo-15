# 0002 — Implantação AWS do TB1 em ECS Fargate via CDK, não Lambda

## Status

Aceita (2026-09-27). Suplanta o trecho da [ADR-0001](0001-stack-scaffold-local.md) que previa o backend "compatível com Lambda via adaptador (Mangum) quando o M4 acontecer". O restante da ADR-0001 segue válido.

## Decisão

No M4, backend e `ai` rodam como serviços **ECS Fargate** a partir dos Dockerfiles existentes, atrás de uma distribuição CloudFront única (`/v1/*` → ALB, o resto → S3 do frontend). Toda a infraestrutura é código **CDK em Python** (`hackathon/infra/`), em us-west-2.

A Lambda foi rejeitada por três motivos: exigiria o adaptador Mangum, o limite de 15 min pode ser estourado pela ingestão com OCR e o cold start aparece na demonstração. O Terraform foi rejeitado porque as credenciais do participante não criam nem leem rede por chamada direta de API. Só o CloudFormation, pelo bootstrap CDK de us-west-2, cria VPC, RDS, ALB e CloudFront na conta do workshop.

Decisões de origem: `requirements/perspec-me/capiwatt-aws-deploy/` (topic-backend-entry, topic-iac-tool, evidência da sondagem de 2026-09-26). Spec: #101.

## Consequências

- O backend não ganha adaptador Lambda. O mesmo container roda no Compose e no ECS, e a paridade local/AWS vem das variáveis de ambiente (`AUTH_MODE`, `DB_*`, `AI_BASE_URL`), não de código por ambiente.
- O deploy depende do bootstrap CDK que o workshop provê em us-west-2 e de Docker na máquina do time, porque as imagens são publicadas pelo `cdk deploy`.
- Voltar para Lambda ou Terraform exige uma nova sondagem de permissões numa conta do workshop antes de suplantar esta ADR.
