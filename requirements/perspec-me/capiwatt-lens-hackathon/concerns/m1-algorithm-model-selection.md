---
concern_id: m1-algorithm-model-selection
concern: ~/.claude/skills/perspec-me/catalog/concerns/m1-algorithm-model-selection/README.md
perspective: model
status: partial
topics:
  - issue-13 — Que estratégia de chunking e que modelo de embeddings do Bedrock se ajustam aos documentos do caso 1?
updated_at: 2026-09-22
---

## Current resolution

O baseline aceito para o caso 1 usa Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`) em `us-east-1`, com vetores `float` normalizados de 1.024 dimensões. A escolha privilegia o único candidato multilíngue já confirmado como autorizado e com acordo disponível na conta do hackathon; seu desempenho para português jurídico continua sujeito ao teste funcional e ao gate de recuperação do corpus real.

A recuperação indexa chunks estruturais pequenos e aplica uma variante *small-to-big* por páginas depois dos três primeiros chunks encontrados. O `Recall@3` continua sendo calculado antes dessa expansão. A contribuição das páginas vizinhas para a resposta e para a correção das citações é avaliada separadamente, evitando atribuir ao modelo de embeddings um ganho produzido apenas pela ampliação de contexto.

## Confirmed facts

- O corpus real disponível contém 10 PDFs jurídicos em português, entre 5 e 71 páginas, com texto extraível por página.
- `amazon.titan-embed-text-v2:0` estava `AUTHORIZED`, com agreement e entitlement `AVAILABLE`, no diagnóstico da conta em `us-east-1` e `us-west-2`.
- `cohere.embed-multilingual-v3` estava autorizado, mas com agreement `NOT_AVAILABLE`; Cohere Embed V4 e Nova Multimodal Embeddings foram listados, mas não testados.
- O adapter atual do módulo `ai` é uma fixture determinística: não produz embeddings nem ranking vetorial real.
- A primeira tentativa de `InvokeModel` em `us-east-1`, com texto jurídico em português e a configuração aceita, falhou em 2026-09-22 com `ExpiredTokenException`; nenhuma resposta vetorial foi produzida.
- O acesso do hackathon só poderá ser renovado mais tarde; Eduardo optou por preparar uma conta AWS pessoal para não manter a validação dependente dessa janela.
- As credenciais da conta pessoal são válidas: `sts:GetCallerIdentity` teve sucesso e identificou um role SSO. Na mesma conta e região, o Titan V2 aparece `ACTIVE`, `AUTHORIZED`, com agreement, entitlement e região `AVAILABLE`.
- Apesar desses estados, `bedrock-runtime:InvokeModel` falhou com `ValidationException: Error 002: Access to Bedrock models is not allowed for this account`; isso indica uma restrição de uso no nível da conta ainda não explicada pela disponibilidade do modelo.
- Uma última tentativa solicitada por Eduardo em 2026-09-22 repetiu exatamente a configuração aceita e retornou novamente o mesmo `Error 002`; a falha foi mantida como pendência operacional e não reabriu as definições de chunking.

## Decisions

- 2026-09-22 (issue-13, Eduardo): selecionar Titan Text Embeddings V2 em `us-east-1`, com 1.024 dimensões e normalização habilitada, como baseline inicial.
- 2026-09-22 (issue-13, Eduardo): usar chunking estrutural com alvo de 600 tokens, máximo de 800 e sobreposição de 100 tokens entre trechos narrativos.
- 2026-09-22 (issue-13, Eduardo): recuperar os três chunks mais relevantes antes de qualquer expansão e calcular `Recall@3` sobre esses três resultados originais.
- 2026-09-22 (issue-13, Eduardo): ampliar cada resultado recuperado para o intervalo completo de páginas atingido pelo chunk, mais a página anterior e a seguinte, mantendo a expansão dentro da mesma versão documental.
- 2026-09-22 (issue-13, Eduardo): comparar chunks de aproximadamente 400 e 800 tokens somente se o baseline não atingir `Recall@3 >= 2/3`.
- 2026-09-22 (issue-13, Eduardo): avaliar separadamente se o contexto ampliado melhora a resposta e a correção das citações, sem misturar esse efeito com a métrica de recuperação.
- 2026-09-22 (issue-13, Eduardo): usar uma conta AWS pessoal com credenciais dedicadas para executar a validação funcional e os testes do Titan V2; a preparação desse acesso foi separada na task #29.
- 2026-09-22 (issue-13, Eduardo): após a última tentativa ainda falhar com `Error 002`, persistir no Map todas as definições de chunking e recuperação já acordadas; a validação funcional permanece explícita e separada, sem invalidar o baseline aceito.

## Derived requirements and constraints

- A configuração reproduzível do modelo registra no mínimo `model_id`, região, dimensões, normalização e `model_version`; cada execução também registra `corpus_version`.
- A mesma configuração de embeddings deve ser usada para documentos e consultas de uma execução; trocar modelo, dimensão ou normalização exige nova versão e reindexação do corpus.
- O teste funcional do Titan deve usar texto jurídico em português e confirmar quantidade de dimensões, normalização e contagem de tokens sem registrar credenciais.
- A avaliação do baseline usa o corpus real e o gabarito da Carolina, colapsando chunks no processo agregado antes de calcular `Recall@3`.
- Se o gate falhar, comparar somente as variantes previstas de chunking, preservando modelo, corpus, consulta, ranking e demais parâmetros para isolar o efeito do tamanho do chunk.
- O experimento deve registrar configuração, perguntas, resultados pré-expansão, contexto expandido, páginas omitidas por orçamento e decisão de aceitar ou revisar o baseline.
- As credenciais pessoais devem ficar fora do repositório e dos Issues, em um perfil AWS local dedicado; o acesso não usa a conta root, concede privilégio mínimo ao Bedrock em `us-east-1` e possui alerta/orçamento de custo.

## Open questions

- A task #29 foi fechada após a configuração e a validação da identidade pessoal, mas seu critério funcional não foi atingido: `InvokeModel` continuou retornando `Error 002`.
- Identificar e remover a restrição de conta que produz `Error 002` apesar de o Titan V2 aparecer autorizado e disponível; verificar cadastro/faturamento da conta e acionar AWS Support se necessário.
- Medir o `Recall@3` do baseline no corpus real; as variantes de 400 e 800 tokens só entram se o gate mínimo falhar.
- Confirmar, nas perguntas do caso da Carolina, se a expansão por páginas adjacentes melhora a resposta e a correção das citações sem exceder o orçamento de contexto.

## Evidence

- `hackathon/scripts/check_aws_capabilities.out` — disponibilidade e autorização dos modelos na conta.
- `hackathon/data/case-1-carolina-mmgd/` — 10 PDFs reais usados para caracterizar o corpus.
- `hackathon/ai/app/routes/index.py` e `hackathon/ai/app/routes/search.py` — adapters atuais sem chunking ou embeddings reais.
- AWS, `Amazon Titan Text Embeddings models` e `Amazon Titan Embeddings G1 - Text` — limite de entrada, segmentação lógica recomendada, dimensões e normalização configuráveis.
- Tentativa de `InvokeModel` de 2026-09-22 — `ExpiredTokenException`, sem vetor retornado.
- GitHub issue #29 — Unblocking task com checklist de acesso pessoal, privilégio mínimo, armazenamento local de credenciais, controle de custo e teste funcional.
- Validação da conta pessoal em 2026-09-22 — identidade e disponibilidade do modelo confirmadas; `InvokeModel` recusado no nível da conta com `Error 002`. Evidência registrada no comentário da task #29.
- Última tentativa de `InvokeModel`, 2026-09-22 — mesma configuração e mesmo `Error 002`; definições confirmadas foram registradas em `Decisions so far` do Map #1. Como a task #29 foi fechada, o Topic aberto e atribuído fica fora da Frontier e de Blocked.

## Topic history

- issue-13: selecionou e persistiu no Map o baseline Titan V2/1.024/normalizado, chunking estrutural e expansão por páginas com avaliação pré/pós-expansão separada. Permanece parcial, aberto e atribuído; a task #29 foi fechada, mas a validação funcional, a calibração e o gate de recuperação seguem pendentes porque a conta ainda recusa `InvokeModel` com `Error 002`.
