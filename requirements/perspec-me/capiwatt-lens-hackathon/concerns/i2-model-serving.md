---
concern_id: i2-model-serving
concern: ~/.claude/skills/perspec-me/catalog/concerns/i2-model-serving/README.md
perspective: infrastructure
status: partial
topics:
  - issue-2 — Qual é o contrato da interface do serviço vetorial (indexar, buscar, agrupar versões) que isola o Bedrock do resto do backend?
  - issue-8 — O que roda local e o que roda na AWS no primeiro ciclo, e como o ambiente local fala com Bedrock e SES (credenciais, custo)?
updated_at: 2026-09-20
---

## Current resolution

**Autoridade de disponibilidade (Eduardo, 2026-09-20):** [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md) prevalece sobre hipóteses do plano e diagnósticos anteriores quanto a serviços, regiões e permissões. Diagnósticos datados permanecem evidência histórica; disponibilidade não equivale à validação funcional do fluxo da aplicação.

**Corte confirmado em 2026-09-20:** Compose local (frontend, backend, `ai`, OpenSearch, Postgres e volumes); apenas embeddings Bedrock remotos, chamados pelo `ai`. `Mailer=preview`, sem SES e sem adoção de SNS. Carolina avalia no PC da equipe. O índice continua sob nosso controle; Bedrock Knowledge Bases não foi adotado. Catálogo do backend no Postgres, atrás dos repositórios de #4/#15; DynamoDB não foi selecionado.

O inventário lista Amazon Titan para embeddings; Titan V2 (`amazon.titan-embed-text-v2:0`) permanece candidato de trabalho, com escolha final na #13 e teste funcional pendente. Respostas de Sonnet 5 e GPT 6 Astra não comprovam a invocação de Titan. Credenciais temporárias do participante entram no Compose por variáveis de ambiente. A identidade do Code Editor é distinta e mais restrita; não se presume que permita embeddings.

**Revisão de 2026-09-25 (Eduardo, sessão de verificação do mapa):** o Bedrock passa a incluir **modelos de geração**, não apenas embeddings. O inventário lista a família Claude (Sonnet 5, Opus 5, Haiku 4.5, Fable 5.1) e a família Nova, e registra que testes por amostragem com credenciais de participante **confirmaram resposta de Claude Sonnet 5** (inventário, linhas 24–27). A escolha do modelo de geração e o contrato do parecer **não são decididos aqui**: pertencem à issue #27 (`o3-ml-functionality`, `u8-cost`), em resolução. SNS continua fora **por escolha, não por indisponibilidade** — o inventário o lista em "Integração" (linha 12).

Registre a assimetria: a geração está comprovada nesta conta, mas a invocação do Titan (embeddings) continua recusada com `Error 002` ([[m1-algorithm-model-selection]]). Um parecer que precisa citar evidência recuperada depende de a recuperação funcionar.

**Exposição (2026-09-25):** a issue #39 ("Demonstração — publicar temporariamente por túnel HTTPS") está aberta e pode mudar a postura registrada em 2026-09-18 ("nenhuma URL pública é exigida"). **A decisão é da #39, não desta página.** Restrição que a #39 precisa pesar: não existe autenticação nem sessão no TB1 — `user_id` é uma string de usuário demo fixa (`hackathon/backend/app/models.py:143-148`).

Regiões permitidas: `us-east-1` e `us-west-2`; padrão `us-east-1`. Provisionamento futuro exige CloudFormation/CDK. IAM permite papéis do time com passagem limitada a Bedrock, AgentCore, ECS, EC2 e EFS; Lambda/CodeBuild recebem `WSParticipantRole`. `AssumeRole` limita-se a `cdk-*`, `admin_persona`, `publisher_persona` e `consumer_persona`. Portanto, “sem IAM próprio” não descreve a disponibilidade atual.

API Gateway permite somente invocar APIs existentes; ECR somente criar/consultar repositórios; EC2 consultar VPCs/subnets e gerenciar launch templates; Application Signals somente `StartDiscovery`. OpenSearch está disponível conforme o inventário; a modalidade Serverless não está explicitada, e o diagnóstico antigo de `aoss:ListCollections` não deve ser generalizado para OpenSearch. Implantação AWS permanece posterior.

## Confirmed facts

- 2026-09-20 (Eduardo): confirmou o corte local proposto e determinou que o documento AWS é a autoridade para disponibilidade de serviços. Os diagnósticos de 2026-09-18 abaixo são históricos.

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

- 2026-09-25 (sessão de verificação do mapa, Eduardo): o Bedrock inclui modelos de geração além de embeddings. A escolha do modelo e o contrato do parecer ficam na issue #27. SNS segue fora por escolha, não por indisponibilidade. Esta decisão **supersede** o trecho "LLM de geração" da linha abaixo, que registrava o escopo daquela revisão, não uma proibição permanente.
- 2026-09-25 (sessão de verificação do mapa, Eduardo): o modelo de ator do TB1 não muda — usuário demo único, sem autenticação. A exposição por túnel HTTPS é decidida na issue #39.

- 2026-09-20 (issue-8, Eduardo): aceitou manter o corte local e incorporar o documento AWS como autoridade de disponibilidade; nenhuma migração para AWS, adoção de SNS ou LLM de geração nesta revisão.

- 2026-09-18 (issue-8, formulação inicial superada pela decisão de prévia e revisão de 2026-09-20): previa Bedrock e SES remotos; vigente: somente Bedrock remoto, sem recursos provisionados no primeiro ciclo.
- 2026-09-18 (issue-8): e-mail sem envio real no primeiro ciclo; port `Mailer` com adapter de prévia; adapter SES adiado até existir conta com SES.
- 2026-09-18 (issue-8): credenciais = variáveis de ambiente com as credenciais temporárias do Workshop Studio (role `WSParticipantRole`), renovadas por sessão; nenhuma identidade IAM própria.
- 2026-09-18 (issue-8): modelo de embeddings da conta = `amazon.titan-embed-text-v2:0` como único candidato comprovadamente autorizado (evidência para #13, que decide).
- 2026-09-18 (issue-8): região padrão `us-east-1` para Bedrock, fixada por configuração (uma só variável), limitada às regiões do inventário autoritativo.

- 2026-09-18 (issue-2): arranjo (a) — Bedrock para embeddings + índice vetorial próprio; Bedrock Knowledge Bases descartado para o primeiro ciclo.
- 2026-09-18 (issue-2): índice vetorial = OpenSearch (container local / Serverless na AWS).

## Derived requirements and constraints

- Qualquer implantação posterior respeita o inventário autoritativo; não presumir nova API Gateway, push ao ECR ou modalidade Serverless. Registrar modelo/perfil exato, região e identidade executora no teste de embeddings, sem segredos e sem substituição silenciosa por fake.

- O adapter Bedrock implementa só embedding; o índice é outro componente atrás do mesmo port (troca de um não obriga troca do outro).
- `model_version` registra o id do modelo Bedrock usado para os vetores do `corpus_version`.
- Precisa existir um adapter local/fake para o embedding (Demo API sem credenciais AWS, plano linha 98) — mesmo que o embedding "real" nunca rode local.

## Open questions

- A issue #39 decide se e como a aplicação é exposta por túnel HTTPS. Enquanto ela não decidir, esta página não afirma exposição pública nem a exclui.
- A escolha do modelo de geração e o contrato do parecer pertencem à issue #27, em resolução. Esta página só registra que a geração está permitida e disponível.

- Revisão de 2026-09-20: permanecem o teste funcional do embedding, a escolha final em #13 e a implantação posterior. O inventário não detalha a modalidade Serverless; não há decisão de implantá-la neste ciclo.

- (issue-8, respondida 2026-09-18 pelo diagnóstico) Bedrock: Titan Text Embeddings V2 invocável em tese (autorizado + entitlement); falta só o teste funcional F1 (`invoke-model`). Cohere multilingual v3 sem acordo — fora. SES: **negado**; não há caminho SES nesta conta.
- (issue-8, respondida 2026-09-18) Credenciais: role assumida — credenciais temporárias do Workshop Studio em variáveis de ambiente do Compose. E-mail: sem envio real neste ciclo (decidido).
- Teste funcional F1 (`bedrock-runtime invoke-model` com Titan V2) ainda não executado — primeiro passo da implementação do adapter, não bloqueia esta especificação.
- M4: a proposta histórica de #2 ("Serverless na AWS") permanece não validada para essa modalidade. O documento autoritativo lista OpenSearch como disponível; arquitetura de implantação fora deste Topic.

- Modelo de embeddings concreto — issue #13 (bloqueada pelos documentos da Carolina).

## Evidence

- [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md), lido em 2026-09-20.
- Eduardo, 2026-09-20: “vamos seguir as sugestões” e “trate esse documento como autoridade para disponibilidade de serviços aws”.

- Map issue #1, Notes.
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 98, 102, 118.

## Topic history

- issue-8 (2026-09-20): revisão de disponibilidade aceita por Eduardo; inventário AWS incorporado como autoridade, corte local preservado. Mantidas as demais decisões desta página.

- issue-8: fixou o corte local/AWS do primeiro ciclo (Compose local; só Bedrock remoto; Carolina avalia no PC local), credenciais temporárias do Workshop Studio por variável de ambiente, Titan V2 como modelo autorizado, e-mail sem envio real (SES indisponível na conta), Postgres no Compose como store do catálogo.

- issue-2: fixou Bedrock-só-embeddings + índice OpenSearch como arranjo do primeiro ciclo; Knowledge Bases e pgvector descartados.
