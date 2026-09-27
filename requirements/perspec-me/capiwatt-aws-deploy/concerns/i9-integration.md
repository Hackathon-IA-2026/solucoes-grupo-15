---
concern_id: i9-integration
concern: ~/.claude/skills/perspec-me/catalog/concerns/i9-integration/README.md
perspective: infrastructure
status: resolved
topics:
  - topic-network
  - topic-catalog-db-hosting
  - topic-backend-entry
  - topic-frontend-hosting
  - topic-cognito-auth
updated_at: 2026-09-26
---

## Current resolution

Na AWS, os componentes se integram numa **VPC própria (CDK, us-west-2, 2 AZs)**:
- **Subnets públicas:** ALB e tasks de computação, com IP público usado só para saída (Bedrock, JWKS do Cognito, SSM).
- **Subnets privadas isoladas**, sem rota para a internet: RDS Postgres e domínio OpenSearch.

Security groups encadeados definem quem fala com quem: internet → `alb-sg` → `backend-sg` → (`db-sg`:5432, `ai-sg`); `ai-sg` → `search-sg`. Não há NAT Gateway. O acesso administrativo é via **SSM Session Manager**, sem porta de entrada aberta e sem chave SSH.

**Postura de segurança — economia consciente, não desconhecimento (Eduardo, 2026-09-26).** As escolhas de rede abaixo foram feitas para economizar num ambiente de hackathon de 72 h e **não devem ser lidas como desconhecimento de segurança**. O time sabe o que um sistema seguro exigiria e optou por não pagar por isso aqui. Numa implantação real, o mínimo seria:
- computação (backend, `ai`) em subnets privadas, com saída por NAT Gateway ou VPC endpoints (`bedrock-runtime`, `s3`, `ecr`, `logs`, `ssm`), sem IP público em nenhuma task;
- HTTPS com domínio e certificado ACM próprios, CloudFront e WAF na frente;
- RDS Multi-AZ, com backups e retenção, criptografia com chave KMS gerenciada pelo cliente e credenciais rotacionadas no Secrets Manager;
- VPC Flow Logs, CloudTrail com retenção, GuardDuty e alarmes;
- OpenSearch com fine-grained access control e sem acesso fora da VPC.

## Confirmed facts

- CloudFormation (cfn-exec-role) cria VPC, subnets, SG e RDS em subnet privada (sondagem 2026-09-26).
- O participante tem `ssm:*` e `ecs:*` em chamada direta, o que permite iniciar sessões SSM e ECS Exec a partir da máquina do time.

## Decisions

- 2026-09-26 (Eduardo, topic-cognito-auth): backend com `AUTH_MODE=none|cognito` (padrão `none` = comportamento atual). Em `cognito`, todo `/v1/*` exceto `/v1/health` exige access token válido do User Pool; `user_id` = claim `username`; `/v1/users/{user_id}/...` responde 403 se o caminho divergir do token; `/v1/ingestions` e `/v1/demo/reset` exigem o grupo `admin`. O contrato HTTP da API não muda. Isso reabre, só para a AWS, o "Out of Scope: autenticação" da #75.

- 2026-09-26 (Eduardo, topic-frontend-hosting): o frontend é publicado pelo `cdk deploy` (`npm run build` + `BucketDeployment` com invalidação) num bucket privado com OAC. Uma CloudFront Function no comportamento padrão faz o fallback de SPA (caminho sem extensão → `/index.html`), sem error responses globais que mascarariam 403/404 da API. A configuração chega em runtime por `/config.json` gerado pelo CDK.

- 2026-09-26 (Eduardo, topic-backend-entry): **uma distribuição CloudFront** é a única entrada pública — `/v1/*` → ALB (backend) e padrão → S3 do frontend (OAC). Mesma origem, sem CORS, HTTPS pelo certificado `*.cloudfront.net`. O SG do ALB aceita só a managed prefix list `com.amazonaws.global.cloudfront.origin-facing`. backend → `ai` por ECS Service Connect (`http://ai:8000`, igual ao Compose). O volume `documents-data` vira **EFS** montado em `/data/documents` nas duas tasks, sem mudança de código.

- 2026-09-26 (Eduardo, topic-catalog-db-hosting): alvo do SSM = ECS Exec com port forwarding (`AWS-StartPortForwardingSessionToRemoteHost`) a partir da task do backend até RDS/OpenSearch; sem bastion EC2. Exige `enableExecuteCommand` e permissões `ssmmessages:*` na task role.

- 2026-09-26 (Eduardo, topic-network): VPC própria em 2 AZs, com subnets públicas e privadas isoladas, sem NAT e com SGs encadeados.
- 2026-09-26 (Eduardo, topic-network): a economia de segurança é deliberada, por ser hackathon, e deve ser documentada como tal junto ao código de rede (postura acima).
- 2026-09-26 (Eduardo, topic-network): OpenSearch vai para a AWS (domínio gerenciado na subnet isolada).
- 2026-09-26 (Eduardo, topic-network): incluir acesso administrativo via SSM.

- 2026-09-26 (Eduardo, topic-cognito-auth): o provisionamento de contas é um script idempotente que lê `COGNITO_USERS` (padrão `carolina,equipe`) e `COGNITO_ADMIN_USERS` (padrão `admin`) do `.env`. Para cada conta, ele roda `admin-create-user --message-action SUPPRESS` com `email=<user_id>@capiwatt.demo` e `email_verified=true`, depois `admin-set-user-password --permanent` com `DEMO_PASSWORD` ou `ADMIN_PASSWORD`, e adiciona as contas admin ao grupo `admin`. Se a conta já existir, só redefine a senha.
- 2026-09-26 (Eduardo, topic-cognito-auth): o User Pool aceita login por username ou e-mail (`signInAliases`), mantém a política de senha padrão do Cognito e não envia e-mail.

## Derived requirements and constraints

- O script de contas falha com mensagem clara se `DEMO_PASSWORD`/`ADMIN_PASSWORD` não cumprir a política padrão (8+ caracteres, maiúscula, minúscula, número, símbolo) ou estiver ausente; as senhas nunca vão para o repositório nem para o `config.json`.
- `.env.example` documenta `COGNITO_USERS`, `COGNITO_ADMIN_USERS`, `DEMO_PASSWORD` e `ADMIN_PASSWORD`.
- Validação de JWT no backend com JWKS em cache (saída pela internet, disponível pelo IP público da task); IDs do pool/client por variável de ambiente injetada pelo CDK.
- Dois app clients: `web` (SRP, sem segredo) e `ops` (`ALLOW_ADMIN_USER_PASSWORD_AUTH`, usado só pelo `seed.sh`).

- O frontend busca `/config.json` ao iniciar, antes de renderizar rotas; o arquivo e o `index.html` são servidos com `Cache-Control: no-cache`.

- O comportamento `/v1/*` do CloudFront não usa cache (CachingDisabled) e repassa `Authorization`, query string e corpo; política de origem AllViewerExceptHostHeader.
- O ALB fica em HTTP:80 atrás do CloudFront (sem certificado próprio); o trecho CloudFront→ALB é HTTP, dentro da postura de economia documentada acima.

- O stack de rede em `hackathon/infra/` precisa carregar a postura de segurança acima num comentário ou README, para que ninguém a leia como descuido.
- Nenhuma task pode aceitar tráfego que não venha do SG da camada anterior; IP público só para saída.
- Se a computação for para subnets privadas (por exemplo, Lambda em VPC), é preciso adicionar NAT ou VPC endpoints no Topic que decidir isso.
- O host do túnel SSM precisa ter caminho de rede até `db-sg`/`search-sg`.

## Open questions



## Evidence

- [Sondagem de capacidades AWS, 2026-09-26](../evidence/2026-09-26-aws-capability-probe.md).

## Topic history

- topic-cognito-auth: AUTH_MODE, verificação do user_id, grupo admin; script idempotente de contas pelo `.env`, senhas fixas, login por username ou e-mail.
- topic-frontend-hosting: publicação, fallback SPA, config em runtime.
- topic-backend-entry: CloudFront como entrada única, Service Connect, EFS.
- topic-network: fixou a topologia da VPC, os SGs, o acesso SSM, o OpenSearch na AWS e a postura de segurança documentada.
