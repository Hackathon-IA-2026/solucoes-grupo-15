---
concern_id: i4-storage
concern: ~/.claude/skills/perspec-me/catalog/concerns/i4-storage/README.md
perspective: infrastructure
status: partial
topics:
  - topic-network
  - topic-catalog-db-hosting
  - topic-vector-index-hosting
  - topic-backend-entry
updated_at: 2026-09-26
---

## Current resolution

O catálogo (Postgres, decidido no Map irmão, com CTE recursiva para o grafo) roda na AWS como **RDS Postgres 16 `db.t4g.micro`**, numa única AZ, na subnet isolada, com 20 GB gp3, sem backup e `RemovalPolicy.DESTROY`; a senha é gerenciada pelo RDS no Secrets Manager. O schema nasce do `create_all` no startup do backend. Os dados de demonstração entram por `POST /v1/ingestions` depois de cada deploy, alimentando catálogo e índice juntos. Nada do Postgres local é migrado. O OpenSearch também vai para a AWS: domínio gerenciado **OpenSearch 2.19**, um nó `t3.small.search`, 10 GB gp3, na subnet isolada, acesso só pelo security group (sem SigV4, sem fine-grained access control), mantendo o cliente atual sem autenticação e o engine `nmslib`. Na AWS entra **só o caso 1**. O índice é populado pelo mesmo seed do catálogo (`POST /v1/ingestions`), sem cadeia própria de carga (topic-vector-index-hosting).

## Confirmed facts

- RDS Postgres 16 (db.t4g.micro, subnets privadas, senha gerenciada pelo RDS) foi criado via CloudFormation em us-west-2; chamada direta de rds:CreateDBInstance é negada.
- EFS e S3 são criáveis por chamada direta e via CloudFormation.

## Decisions

- 2026-09-26 (Eduardo, topic-backend-entry): originais e texto extraído ficam em **EFS** montado em `/data/documents` no backend e no `ai` (mesmo contrato do volume do Compose); S3 rejeitado por exigir mudança de código.

- 2026-09-26 (Eduardo, topic-catalog-db-hosting): RDS db.t4g.micro em uma única AZ, sem backup; seed por `/v1/ingestions`, sem dump do local; ECS em vez de container Postgres rejeitado.

- 2026-09-26 (Eduardo, topic-network): RDS e OpenSearch ficam em subnets privadas isoladas da VPC própria; o OpenSearch vai para a AWS.
- 2026-09-26 (Eduardo, topic-vector-index-hosting): OpenSearch 2.19, um nó `t3.small.search`, 10 GB gp3, protegido só pelo SG; nenhuma mudança no código do `ai`; só o caso 1 (`data/case-1-carolina-mmgd`, 12 MB) é carregado na AWS; a cadeia S3 → task de carga → EFS da rodada 7 foi descartada.

## Derived requirements and constraints

- `app/config.py` precisa montar `DATABASE_URL` a partir de `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` quando `DATABASE_URL` estiver ausente; o Compose continua usando `DATABASE_URL`.
- A task do backend recebe usuário e senha como *secrets* do ECS (segredo do RDS), nunca como texto em variável de ambiente.
- `hackathon/infra/scripts/seed.sh` chama `POST /v1/ingestions` depois do deploy.
- O domínio precisa aceitar HTTP sem autenticação dentro da VPC: sem fine-grained access control, access policy aberta ao principal `*` restrita pela VPC/SG, e `OPENSEARCH_URL` do `ai` apontando para o endpoint do domínio (HTTPS 443; o cliente atual aceita a URL completa).
- Engine fica em `nmslib`, que exige versão 2.x (o 3.x bloqueia `nmslib` em índices novos); não subir para 3.x sem revisar o código.

## Open questions

- Confirmar no deploy que `t3.small.search` suporta o plugin k-NN com `nmslib` (se não suportar, subir para `m6g.large.search` ou similar, sem mudar código).


## Evidence

- [Sondagem de capacidades AWS, 2026-09-26](../evidence/2026-09-26-aws-capability-probe.md) (`dw-aws-capability-probe`).
- Código do `ai`: `ai/app/vector_store.py` (cliente sem autenticação, `nmslib`), `ai/app/routes/index.py` (index/reindex re-embedam).

## Topic history

- topic-catalog-db-hosting: fixou RDS, credenciais, schema e seed.
- topic-network: dados em subnets isoladas; OpenSearch na AWS.
- topic-vector-index-hosting: fixou domínio OpenSearch, acesso por SG, carga pelo seed e corpus = caso 1.
- dw-aws-capability-probe: evidência de permissões diretas vs. CloudFormation via bootstrap CDK.
