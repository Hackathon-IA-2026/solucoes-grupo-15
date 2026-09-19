---
concern_id: i2-model-serving
concern: ~/.claude/skills/perspec-me/catalog/concerns/i2-model-serving/README.md
perspective: infrastructure
status: partial
topics:
  - issue-2 — Qual é o contrato da interface do serviço vetorial (indexar, buscar, agrupar versões) que isola o Bedrock do resto do backend?
  - issue-8 — O que roda local e o que roda na AWS no primeiro ciclo, e como o ambiente local fala com Bedrock e SES (credenciais, custo)?
updated_at: 2026-09-18
---

## Current resolution

No primeiro ciclo, o "Bedrock" atrás do port do serviço vetorial ([[i9-integration]]) é **Bedrock somente para embeddings** (modelo de embeddings via Bedrock Runtime API — Titan ou Cohere, escolha na issue #13) **mais um índice vetorial que nós controlamos**. Não se adota Bedrock Knowledge Bases: ele decidiria chunking por nós, tornaria o agrupamento por família um pós-processamento e inviabilizaria rodar a busca localmente. Consumo: o adapter chama o Bedrock apenas para gerar vetores; recuperação e ranking rodam no nosso índice.

Índice vetorial: **OpenSearch** — container local no Compose, OpenSearch Serverless na AWS (decisão de Eduardo, 2026-09-18; pgvector descartado). Como o embedding é servido: o módulo `ai` chama o Bedrock Runtime a partir do adapter `BedrockEmbedder`; o `backend` nunca fala com Bedrock. **Corte do primeiro ciclo (issue-8, Eduardo, 2026-09-18): "local com duas dependências remotas".** Todo o produto roda no Compose numa máquina da equipe (frontend, backend, ai, OpenSearch, volume compartilhado); as únicas chamadas que saem da máquina são `bedrock:InvokeModel` (do `ai`, embeddings) e `ses:SendEmail` (do `backend`, notificações). Lambda, API Gateway, DynamoDB, S3 e OpenSearch Serverless ficam para o M4 (implantação), fora deste ciclo. A Carolina avalia o TB1 **acessando localmente o PC que roda a aplicação** — não há necessidade de URL implantada no primeiro ciclo.

A conta AWS é a **do hackathon (AWS Workshop Studio, ambiente temporário de 72 h; regiões `us-east-1`/`us-west-2`; Bedrock e CloudWatch citados; centrado em Bedrock AgentCore)** — região indiferente para a equipe; `us-east-1` é o padrão até o diagnóstico dizer o contrário. Diagnóstico de 2026-09-18: **Bedrock viável** (Titan Text Embeddings V2 autorizado e com entitlement nas duas regiões; Cohere multilingual sem acordo — descartado como candidato); **SES inacessível** nesta conta (toda operação SES negada pela política do `WSParticipantRole`); OpenSearch Serverless também negado. A identidade é uma role assumida com credenciais temporárias — não há como criar usuário IAM próprio; o Compose recebe as credenciais do Workshop Studio por variáveis de ambiente, renovadas a cada sessão. **E-mail (Eduardo, 2026-09-18): sem envio real no primeiro ciclo** — o port `Mailer` existe desde já, com o adapter de prévia (`log`/preview: e-mail renderizado gravado no volume e exibido na página inicial) como único adapter ativo; o adapter SES fica para quando houver conta com SES (M4 ou evolução). Isso revisa a decisão da reunião "SES desde o início" à luz da conta do hackathon; a notificação na página inicial continua obrigatória (#6).

**Store do catálogo do backend (Eduardo, 2026-09-18): Postgres em container no Compose**, atrás dos repositórios com interface própria já decididos (#4/#15) — DynamoDB descartado para o catálogo.

## Confirmed facts

- 2026-09-18 (issue-8, diagnóstico `hackathon/scripts/check_aws_capabilities.out`, 23:11 UTC): identidade = role assumida `WSParticipantRole` (credenciais temporárias com session token); `iam:SimulatePrincipalPolicy` negado; conta `542260303569`.
- 2026-09-18 (issue-8, diagnóstico): Bedrock acessível em `us-east-1` e `us-west-2`; `amazon.titan-embed-text-v2:0` e `titan-embed-text-v1` com `authorizationStatus: AUTHORIZED`, agreement e entitlement `AVAILABLE` nas duas regiões; `cohere.embed-multilingual-v3` com `agreementAvailability: NOT_AVAILABLE` (sem acordo de marketplace nesta conta). Também listados `cohere.embed-v4:0` e `amazon.nova-2-multimodal-embeddings-v1:0` (não testados).
- 2026-09-18 (issue-8, diagnóstico): **SES negado em todas as operações de leitura nas duas regiões** (`ses:GetAccount`, `ses:ListEmailIdentities`, `ses:GetSendQuota` — "no identity-based policy allows"); `ses:SendEmail` não foi testado mas nada na política cobre SES.
- 2026-09-18 (issue-8, diagnóstico): CloudWatch Logs, S3 (list), Lambda (list), DynamoDB (list, vazio) e Bedrock AgentCore acessíveis; **OpenSearch Serverless negado** (`aoss:ListCollections`). Existe uma Lambda `BedrockCostTrackerLambda` do workshop — o consumo de Bedrock é monitorado pelo organizador.
- 2026-09-18 (issue-8, Eduardo): a Carolina acessa localmente o PC que roda a aplicação para avaliar o TB1; nenhuma URL pública é exigida no primeiro ciclo.
- 2026-09-18 (issue-8, Eduardo): a conta AWS é a do hackathon — AWS Workshop Studio, 72 h, regiões `us-east-1` e `us-west-2`, Bedrock e CloudWatch explicitamente mencionados, workshop centrado em Bedrock AgentCore. Isso não comprova quais recursos estão autorizados. Região indiferente para a equipe.

- Reunião 2026-09-17: Bedrock para busca vetorial desde o início; o máximo possível roda local.
- Plano (linha 118): "Bedrock fornece as capacidades de modelo"; "vetores de modelos diferentes não devem ser misturados".
- Plano (linha 102): banco vetorial fora da memória temporária das funções.

## Decisions

- 2026-09-18 (issue-8): corte do primeiro ciclo = Compose local + apenas Bedrock (embeddings, via `ai`) e SES (e-mail, via `backend`) como chamadas remotas; Lambda/API Gateway/DynamoDB/S3/OpenSearch Serverless só no M4.
- 2026-09-18 (issue-8): e-mail sem envio real no primeiro ciclo; port `Mailer` com adapter de prévia; adapter SES adiado até existir conta com SES.
- 2026-09-18 (issue-8): credenciais = variáveis de ambiente com as credenciais temporárias do Workshop Studio (role `WSParticipantRole`), renovadas por sessão; nenhuma identidade IAM própria.
- 2026-09-18 (issue-8): modelo de embeddings da conta = `amazon.titan-embed-text-v2:0` como único candidato comprovadamente autorizado (evidência para #13, que decide).
- 2026-09-18 (issue-8): região padrão `us-east-1` para Bedrock e SES, fixada por configuração (uma só variável), revisável pelo diagnóstico da conta.

- 2026-09-18 (issue-2): arranjo (a) — Bedrock para embeddings + índice vetorial próprio; Bedrock Knowledge Bases descartado para o primeiro ciclo.
- 2026-09-18 (issue-2): índice vetorial = OpenSearch (container local / Serverless na AWS).

## Derived requirements and constraints

- O adapter Bedrock implementa só embedding; o índice é outro componente atrás do mesmo port (troca de um não obriga troca do outro).
- `model_version` registra o id do modelo Bedrock usado para os vetores do `corpus_version`.
- Precisa existir um adapter local/fake para o embedding (Demo API sem credenciais AWS, plano linha 98) — mesmo que o embedding "real" nunca rode local.

## Open questions

- (issue-8, respondida 2026-09-18 pelo diagnóstico) Bedrock: Titan Text Embeddings V2 invocável em tese (autorizado + entitlement); falta só o teste funcional F1 (`invoke-model`). Cohere multilingual v3 sem acordo — fora. SES: **negado**; não há caminho SES nesta conta.
- (issue-8, respondida 2026-09-18) Credenciais: role assumida, sem IAM próprio — credenciais temporárias do Workshop Studio em variáveis de ambiente do Compose. E-mail: sem envio real neste ciclo (decidido).
- Teste funcional F1 (`bedrock-runtime invoke-model` com Titan V2) ainda não executado — primeiro passo da implementação do adapter, não bloqueia esta especificação.
- M4 nesta conta: OpenSearch Serverless negado — a decisão de #2 ("Serverless na AWS") não vale para a conta do hackathon; a implantação, se acontecer, precisa de outro destino para o índice. Fora deste Topic.

- Modelo de embeddings concreto — issue #13 (bloqueada pelos documentos da Carolina).

## Evidence

- Map issue #1, Notes.
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 98, 102, 118.

## Topic history

- issue-8: fixou o corte local/AWS do primeiro ciclo (Compose local; só Bedrock remoto; Carolina avalia no PC local), credenciais temporárias do Workshop Studio por variável de ambiente, Titan V2 como modelo autorizado, e-mail sem envio real (SES indisponível na conta), Postgres no Compose como store do catálogo.

- issue-2: fixou Bedrock-só-embeddings + índice OpenSearch como arranjo do primeiro ciclo; Knowledge Bases e pgvector descartados.
