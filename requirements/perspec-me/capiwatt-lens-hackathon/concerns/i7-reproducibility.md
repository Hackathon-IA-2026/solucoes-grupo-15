---
concern_id: i7-reproducibility
concern: ~/.claude/skills/perspec-me/catalog/concerns/i7-reproducibility/README.md
perspective: infrastructure
status: resolved
topics:
  - issue-8 — O que roda local e o que roda na AWS no primeiro ciclo, e como o ambiente local fala com Bedrock e SES (credenciais, custo)?
  - issue-9 — Como corpus_version, model_version e ranking_version são registrados para reproduzir uma execução?
updated_at: 2026-09-20
---

## Current resolution

**Autoridade de disponibilidade (Eduardo, 2026-09-20):** [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md) prevalece sobre hipóteses do plano e diagnósticos anteriores quanto a serviços, regiões e permissões. Diagnósticos datados permanecem evidência histórica; disponibilidade não equivale à validação funcional do fluxo da aplicação.

**Revisão da issue-8 (2026-09-20, aceita por Eduardo):** o corte local e a reexecução offline da #9 permanecem. A configuração de Bedrock registra a região e o identificador exato do modelo/perfil validado com a identidade executora do `ai`; as permissões restritas do Code Editor não são usadas como descrição das permissões de participante.

A reprodutibilidade do primeiro ciclo é ancorada no ambiente local: o Compose sobe sem credenciais com `EMBEDDER=fake` e `MAILER=preview`, e a suíte de testes nunca toca a AWS. Bedrock entra por configuração explícita para gerar embeddings reais; SES está indisponível neste ciclo, conforme a decisão da issue-8. A conta AWS é temporária (72 h).

Na issue-9, Eduardo confirmou a reexecução sem AWS das buscas registradas de avaliação e demonstração, a igualdade nas fixtures e a preservação de cada corpus usado nessas atividades até o encerramento do hackathon. Isso exige preservar localmente os embeddings dos documentos e das consultas, além dos originais e do catálogo; o embedder fake não substitui o modelo real na reexecução. A afirmação anterior de que apenas `pg_dump` e originais bastam é refinada por esse requisito. As três versões apontam para registros imutáveis conforme [M10](m10-versioning.md); o backend registra a execução com os identificadores efetivamente usados pelo módulo `ai`. Na busca real, diferenças são registradas e comparadas, sem exigência de igualdade exata. Resolvido para o primeiro ciclo do hackathon, com aceite de Eduardo em 2026-09-18.

## Confirmed facts

- 2026-09-20 (Eduardo): confirmou o corte local proposto e determinou que o documento AWS é a autoridade para disponibilidade de serviços. Os diagnósticos de 2026-09-18 abaixo são históricos.

- 2026-09-18 (issue-8, diagnóstico `hackathon/scripts/check_aws_capabilities.out`, 23:11 UTC): identidade = role assumida `WSParticipantRole` (credenciais temporárias com session token); `iam:SimulatePrincipalPolicy` negado; conta `542260303569`.
- 2026-09-18 (issue-8, diagnóstico): Bedrock acessível em `us-east-1` e `us-west-2`; `amazon.titan-embed-text-v2:0` e `titan-embed-text-v1` com `authorizationStatus: AUTHORIZED`, agreement e entitlement `AVAILABLE` nas duas regiões; `cohere.embed-multilingual-v3` com `agreementAvailability: NOT_AVAILABLE` (sem acordo de marketplace nesta conta). Também listados `cohere.embed-v4:0` e `amazon.nova-2-multimodal-embeddings-v1:0` (não testados).
- 2026-09-18 (issue-8, diagnóstico): **SES negado em todas as operações de leitura nas duas regiões** (`ses:GetAccount`, `ses:ListEmailIdentities`, `ses:GetSendQuota` — "no identity-based policy allows"); `ses:SendEmail` não foi testado mas nada na política cobre SES.
- 2026-09-18 (issue-8, diagnóstico): CloudWatch Logs, S3 (list), Lambda (list), DynamoDB (list, vazio) e Bedrock AgentCore acessíveis; **OpenSearch Serverless negado** (`aoss:ListCollections`). Existe uma Lambda `BedrockCostTrackerLambda` do workshop — o consumo de Bedrock é monitorado pelo organizador.
- Plano (linha 98): a Demo API deve funcionar sem credenciais AWS; originais, metadados e registros de execução em volumes persistentes.
- Plano (linha 118): trocar o modelo de embeddings exige reindexar e repetir a avaliação; vetores de modelos diferentes não se misturam.
- Plano (linha 201): cada entrega registra a LoD e o ambiente (local ou AWS).
- 2026-09-18 (issue-8, Eduardo): conta AWS temporária (72 h).
- 2026-09-18 (issue-9, Eduardo): confirmou "reexecutar sem aws", "igualdade nas fixtures" e a retenção proposta dos corpora de avaliação e demonstração.
- 2026-09-18 (issue-9, Eduardo): "aceito as sugestões" confirmou o contrato das versões, a comparação de diferenças na busca real e o encerramento do Topic.

## Decisions

- 2026-09-20 (issue-8, Eduardo): mantida a reprodutibilidade local; inventário AWS é autoridade de disponibilidade, com validação funcional do embedding separada.

- 2026-09-18 (issue-8): o Compose e os testes rodam sem credenciais AWS; Bedrock entra só por configuração explícita (`EMBEDDER=bedrock`), nunca por padrão; `MAILER=preview` é o único adapter de e-mail ativo neste ciclo.
- 2026-09-18 (issue-8, refinada pela issue-9): catálogo em Postgres no Compose, com volume próprio; `pg_dump` do catálogo + volume de originais preservam a base documental. Para reexecutar sem AWS, preservar também os embeddings reais usados; o índice OpenSearch continua derivado.
- 2026-09-18 (issue-9): reexecutar localmente, sem AWS, as buscas registradas de avaliação e demonstração.
- 2026-09-18 (issue-9): fixtures devem retornar os mesmos resultados na mesma ordem; na busca real, registrar e comparar eventuais diferenças, sem exigir igualdade exata. O critério de qualidade contra o gabarito pertence à issue-11.
- 2026-09-18 (issue-9): preservar cada corpus usado em avaliação ou demonstração até o encerramento do hackathon; versões intermediárias sem evidência associada podem ser descartadas.
- 2026-09-18 (issue-9): o backend registra entrada efetiva, `request_id`, `data_mode`, `corpus_version`, `model_version`, `ranking_version`, vetor da consulta, resposta ordenada e referência ao código e ambiente com dependências fixadas. O módulo `ai` fornece as versões e os artefatos efetivamente usados.

## Derived requirements and constraints

- Registrar no teste funcional a identidade executora (sem credenciais), região e modelo/perfil efetivamente usado; manter as versões e embeddings reais exigidos pela #9.

- Embedder fake determinístico (mesma entrada → mesmo vetor) para testes e Demo API.
- `model_version` registra id do modelo Bedrock + região; `corpus_version` registra qual embedder gerou o índice — avaliações comparam só `corpus_version` do mesmo embedder.
- Credenciais AWS nunca no repositório: `.env.example` versionado, `.env` ignorado; credenciais temporárias do Workshop Studio entram como variáveis de ambiente.
- Toda a fonte de verdade (originais, catálogo, gabarito, resultados de avaliação) em volumes locais; a AWS é descartável.
- A reexecução offline deve reutilizar os embeddings reais dos documentos e da consulta registrada, sem invocar Bedrock nem trocar pelo embedder fake.
- Os artefatos necessários à reexecução acompanham a retenção do corpus associado à avaliação ou demonstração; não basta conservar apenas seu identificador.
- Reexecutar significa rodar novamente a recuperação e o ranking sobre o corpus preservado, usando o vetor da consulta registrada; consultar a resposta salva não satisfaz esse requisito.
- A garantia offline cobre consultas registradas; gerar embeddings para perguntas novas pode continuar exigindo Bedrock.
- Preservar a versão do código (commit Git) e as dependências fixadas, incluindo as versões das imagens do ambiente local, junto da referência da execução.

## Open questions

- Nenhuma pendência para a issue-9 no primeiro ciclo. A qualidade contra o gabarito é tratada na issue-11 e não bloqueia este contrato de reexecução.

## Evidence

- [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md), lido em 2026-09-20.
- Eduardo, 2026-09-20: “vamos seguir as sugestões” e “trate esse documento como autoridade para disponibilidade de serviços aws”.

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 98, 118, 201.
- Sessão perspec-me da issue-9, resposta de Eduardo em 2026-09-18: "1. reexecutar sem aws 2. igualdade nas fixtures 3. podemos sim".
- Sessão perspec-me da issue-9, aceite final de Eduardo em 2026-09-18: "aceito as sugestões".

## Topic history

- issue-8 (2026-09-20): revisão de disponibilidade aceita por Eduardo; inventário AWS incorporado como autoridade, corte local preservado. Mantidas as demais decisões desta página.

- issue-8: criou a página; reprodutibilidade ancorada no Compose sem credenciais (Postgres + volumes como fonte de verdade), AWS tratada como descartável (72 h).
- issue-9: resolveu o contrato de reexecução offline com embeddings preservados, igualdade nas fixtures, comparação de variações reais e retenção dos corpora de avaliação e demonstração; Topic encerrado com aceite de Eduardo.
