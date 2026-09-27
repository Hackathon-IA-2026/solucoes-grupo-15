**Backend:** local — Wayfinder map issue: [CapiWatt Lens — Implantação AWS (M4): mapa de decisões](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/89) — Topics espelhados como sub-issues: #90 (índice vetorial) e #91 (Cognito), resolvidos localmente; #99 (observabilidade) e #100 (TB1 AWS × local), resolvidos localmente em 2026-09-27

# CapiWatt Lens — Implantação AWS (M4) — Map

Seed: pedido de Eduardo em 2026-09-26 — "usando a issue #75 e todas as suas subissues, sessão sobre a arquitetura AWS; implementar o máximo possível com Terraform, criar VPC se necessário para o banco de dados, incluir Cognito para o frontend". Map irmão (não substitui): [capiwatt-lens-hackathon](../capiwatt-lens-hackathon/MAP.md), cuja Destination não cobre implantação.

## Destination

A arquitetura de implantação do TB1 na conta do hackathon está decidida o suficiente para virar tickets de implementação sem reabrir decisão de projeto: ferramenta de IaC comprovada na conta, rede, onde rodam Postgres/OpenSearch/arquivos, porta de entrada HTTPS do backend, hospedagem do frontend e login via Cognito com o `user_id` do backend derivado do token — mantendo o Compose local funcionando como hoje —, além da observabilidade mínima na AWS e do critério para comparar o TB1 repetido na AWS com a avaliação local (saída do M4).

_Confirmada por Eduardo em 2026-09-26; ampliada em 2026-09-27 (observabilidade e comparação AWS × local) por delegação de Eduardo em topic-tb1-aws-vs-local._

## Current understanding

O TB1 roda hoje só no Compose local (backend F3 da #75 completo, sub-issues #76–#82 fechadas, 92/92 testes). O [inventário AWS](../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md) — autoridade de disponibilidade — restringe a arquitetura: provisionamento "via CloudFormation ou CDK"; EC2 só consulta VPC/subnet; sem RDS/Aurora, ALB ou CloudFront; API Gateway só invoca APIs existentes; Lambda usa o `WSParticipantRole` como papel; papéis próprios só para ECS/EC2/EFS/Bedrock; conta de 72 h. Preferência de IaC: Terraform; plano B: CDK em Python (Eduardo, 2026-09-26). A sondagem `dw-aws-capability-probe` bloqueia os Topics de base.

## Perspective resolution

| Perspective | unexamined | open | partial | resolved | deferred | not-applicable | superseded |
|---|---|---|---|---|---|---|---|
| O — System Objectives | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| U — User Experience | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| I — Infrastructure | 0 | 0 | 4 | 3 | 0 | 0 | 0 |
| M — Model | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| D — Data | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Decisions so far

- 2026-09-26 — Destination confirmada; plano B de IaC = CDK em Python (Eduardo).
- [topic-iac-tool](topics/topic-iac-tool.md) — CDK em Python para toda a infraestrutura, us-west-2 (bootstrap existente, cfn-exec-role admin), `hackathon/infra/` com um stack por grupo, deploy local assumindo o deploy-role; Terraform abandonado (sem rede por chamada direta). Concerns: [I8](concerns/i8-maintainability.md) `partial`, [I7](concerns/i7-reproducibility.md) `partial`.
- [topic-network](topics/topic-network.md) — VPC própria (2 AZs), subnets públicas (ALB, tasks com IP só de saída) e isoladas (RDS, OpenSearch), sem NAT, SGs encadeados, acesso via SSM; OpenSearch vai para a AWS (Fog graduado em [topic-vector-index-hosting](topics/topic-vector-index-hosting.md)). **Economia de segurança deliberada por ser hackathon, documentada, e não desconhecimento.** Concerns: [I9](concerns/i9-integration.md) `partial`, [I4](concerns/i4-storage.md) `open`.
- [topic-catalog-db-hosting](topics/topic-catalog-db-hosting.md) — RDS Postgres 16 db.t4g.micro (uma AZ, sem backup, senha gerenciada), `config.py` monta a URL de variáveis separadas, schema por `create_all`, seed por `POST /v1/ingestions` pós-deploy, SSM = ECS Exec com port forwarding. Concerns: [I4](concerns/i4-storage.md) `partial`, [I7](concerns/i7-reproducibility.md) `partial`, [I11](concerns/i11-cost.md) `open`.
- [topic-backend-entry](topics/topic-backend-entry.md) — ECS Fargate para backend e `ai` (Dockerfiles existentes), Service Connect entre eles, uma distribuição CloudFront (`/v1/*`→ALB, padrão→S3) na mesma origem, ALB fechado à prefix list do CloudFront, EFS no lugar do volume `documents-data` (Fog resolvido), Bedrock por task role, DynamoDB da #83 no CDK; Lambda rejeitada. Concerns: [I2](concerns/i2-model-serving.md) `partial`, [I9](concerns/i9-integration.md), [I4](concerns/i4-storage.md), [I11](concerns/i11-cost.md).
- [topic-frontend-hosting](topics/topic-frontend-hosting.md) — `BucketDeployment` no `cdk deploy`, CloudFront Function para o fallback SPA (preserva 403/404 da API), `config.json` em runtime; sem Cognito → modo demo local sem login. Concerns: [I9](concerns/i9-integration.md), [U6](concerns/u6-acceptance.md) `partial`.
- [topic-cognito-auth](topics/topic-cognito-auth.md) — login SRP no app (Amplify, sem Hosted UI, sem auto-cadastro), backend `AUTH_MODE=none|cognito` com `user_id` = `username` do access token, 403 fora do próprio caminho, grupo `admin` para ingestão/reset; contas `carolina`/`equipe`/`admin` (extras via `.env`) por script idempotente, senhas fixas (`DEMO_PASSWORD` compartilhada, `ADMIN_PASSWORD` separada), login por e-mail ou usuário. Concerns: [I9](concerns/i9-integration.md) `resolved`, [U6](concerns/u6-acceptance.md) `resolved`, [I6](concerns/i6-telemetry.md) `partial`.
- [topic-vector-index-hosting](topics/topic-vector-index-hosting.md) — OpenSearch 2.19 gerenciado (`t3.small.search`, 10 GB, só SG, `nmslib`), populado pelo seed `/v1/ingestions` com só o caso 1; Bedrock segue em us-east-1 (testado, substitui o padrão us-west-2 de topic-backend-entry); **nenhuma mudança no código do `ai`**. Concerns: [I4](concerns/i4-storage.md), [I2](concerns/i2-model-serving.md), [I7](concerns/i7-reproducibility.md) `partial`.
- [topic-aws-observability](topics/topic-aws-observability.md) (#99, 2026-09-27, Eduardo por delegação) — `awslogs` com um grupo por serviço (`/capiwatt/backend`, `/capiwatt/ai`), retenção de 3 dias; linha JSON por requisição no backend com `user_id`, `trace_id` (`X-Amzn-Trace-Id`) e `search_request_id`, que liga à `SearchExecution`/replay; `ai` sem mudança de código; borda só com métricas gratuitas; limite de atribuição da senha compartilhada aceito; custo total do M4 ≈ US$ 13 em 72 h. Concerns: [I6](concerns/i6-telemetry.md) `resolved`, [I11](concerns/i11-cost.md) `resolved`.
- [topic-tb1-aws-vs-local](topics/topic-tb1-aws-vs-local.md) (#100, 2026-09-27, Eduardo por delegação) — comparação entra na Destination; caso 1 e a pergunta com gabarito; baseline = `results.json` commitado; AWS pela API pública com token de `equipe`; gate = mesmas versões, mesmo conjunto de processos no top 3 e mesmo `Recall@3` (2/3); ordem e |Δscore| ≤ 0,001 só informativos; artefato `output/aws_vs_local.json`. Concerns: [M5](concerns/m5-performance-metrics.md) `resolved`, [I7](concerns/i7-reproducibility.md) `partial`.

## Frontier

_Renderização de **list frontier** em 2026-09-27:_

- (vazia — todos os Topics resolvidos)

## Blocked

_Renderização em 2026-09-27:_

- (nenhum)

## Fog

_(vazio — as duas entradas viraram [topic-aws-observability](topics/topic-aws-observability.md) e [topic-tb1-aws-vs-local](topics/topic-tb1-aws-vs-local.md) em 2026-09-26)_

## Delegated work

### dw-aws-capability-probe

- type: unblocking-task
- question: O WSParticipantRole consegue, por chamada direta de API (como o Terraform faz), criar e destruir os recursos candidatos — S3, security group/VPC, ECS cluster/serviço, EFS, Lambda + Function URL, Cognito User Pool, OpenSearch domain, ECR, papéis IAM para ECS — e existe VPC padrão utilizável?
- blocks: topic-iac-tool
- status: resolved
- created_at: 2026-09-26
- resolved_at: 2026-09-26
- checklist:
  - rodar sondagem com credenciais de `.env` em us-east-1, criando e destruindo cada recurso mínimo
  - repetir um recurso via `terraform apply`/`destroy` para confirmar o caminho do provider
- result:
    answer: Chamada direta (Terraform com WSParticipantRole) só cobre S3, Cognito, ECR (criar), EFS, OpenSearch, DynamoDB, SSM, Logs — nada de VPC/SG (nem leitura de atributos da VPC), Lambda inviável, task role do ECS e RDS/ALB/CloudFront negados. CloudFormation via bootstrap CDK em us-west-2 (cfn-exec-role = AdministratorAccess) criou VPC, subnets, SG, RDS Postgres, ALB, CloudFront OAC, Lambda + Function URL e ECS task definition com papéis.
    evidence: evidence/2026-09-26-aws-capability-probe.md
    sources: execução dos scripts de sondagem com as credenciais de `.env` (2026-09-26)
    affected_concerns:
      - i8-maintainability
      - i4-storage
      - i2-model-serving
    new_topics: []

## Out of scope

## Handoff readiness
