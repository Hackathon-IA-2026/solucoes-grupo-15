---
concern_id: m1-algorithm-model-selection
concern: ~/.claude/skills/perspec-me/catalog/concerns/m1-algorithm-model-selection/README.md
perspective: model
status: partial
topics:
  - issue-13 — Que estratégia de chunking e que modelo de embeddings do Bedrock se ajustam aos documentos do caso 1?
updated_at: 2026-09-26
---

## Current resolution

O baseline aceito para o caso 1 usa Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`) em `us-east-1`, com vetores `float` normalizados de 1.024 dimensões. A escolha privilegia o único candidato multilíngue já confirmado como autorizado e com acordo disponível na conta do hackathon. Em 2026-09-26, a invocação funcional foi confirmada com sucesso (ver Confirmed facts) — o baseline deixa de estar bloqueado por acesso.

**Modelo travado em 2026-09-26 (decisão de Eduardo)**: Titan V2 é o modelo final do baseline, não apenas provisório. `cohere.embed-v4:0` e `amazon.nova-2-multimodal-embeddings-v1:0` (ambos `ACTIVE` na conta, nunca testados) só entram como candidatos se o baseline não atingir `Recall@3 >= 2/3` no corpus real — o mesmo gatilho já usado para as variantes de chunk de ~400/800 tokens, sem um segundo critério de acionamento. A execução da própria medição de `Recall@3` foi explicitamente adiada por Eduardo em 2026-09-26 (não é prioridade agora); segue como trabalho de acompanhamento fora deste interview, não como bloqueio desta Topic.

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
- Em 2026-09-26, Eduardo forneceu novas credenciais temporárias em `.env` (conta `640205779371`, `arn:aws:sts::640205779371:assumed-role/WSParticipantRole/Participant` — uma terceira identidade, distinta tanto da conta do hackathon original (`542260303569`) quanto da conta pessoal da task #29 (`154201758548`); a região da sessão (`AWS_DEFAULT_REGION=us-west-2`) diverge da região usada na chamada (`us-east-1`), passada explicitamente).
- `bedrock:GetFoundationModelAvailability` para `amazon.titan-embed-text-v2:0` em `us-east-1` com essas credenciais retornou `authorizationStatus: AUTHORIZED`, `agreementAvailability/entitlementAvailability/regionAvailability: AVAILABLE` — mesmo estado de disponibilidade já visto nas contas anteriores.
- **Invocação funcional bem-sucedida em 2026-09-26**: `bedrock-runtime invoke-model` com `amazon.titan-embed-text-v2:0`, `us-east-1`, `dimensions=1024`, `normalize=true`, usando um texto jurídico em português de teste (ANEEL/REN 1000/2021), retornou um vetor `float` de 1.024 dimensões, norma euclidiana ≈ 1,0 (confirma a normalização) e `inputTextTokenCount=42`; nenhum erro. É a primeira invocação funcional bem-sucedida registrada nesta Concern — `Error 002`/`ExpiredTokenException` não se repetiram com esta identidade.

## Decisions

- 2026-09-26 (issue-13, Eduardo): travar Titan V2 como modelo final do baseline; Cohere Embed V4 e Nova Multimodal Embeddings só são testados se o gate `Recall@3` falhar, mesmo gatilho das variantes de chunk.
- 2026-09-26 (issue-13, Eduardo): não executar ainda a medição de `Recall@3` no corpus real — adiada, sem prazo definido nesta sessão.
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

- A task #29 foi fechada após a configuração e a validação da identidade pessoal, mas seu critério funcional não foi atingido com aquela conta: `InvokeModel` continuou retornando `Error 002`. **Resolvido por outra via em 2026-09-26**: uma terceira identidade temporária (conta `640205779371`) invocou o modelo com sucesso; a causa raiz do `Error 002` na conta pessoal (`154201758548`) não foi identificada e permanece sem explicação, mas deixou de bloquear o baseline.
- **Resolvido em 2026-09-26**: modelo travado em Titan V2 (ver Decisions); alternativas só entram se o gate `Recall@3` falhar.
- Medir o `Recall@3` do baseline no corpus real — executável desde que a invocação funcional foi validada, mas **explicitamente adiado por Eduardo em 2026-09-26**, sem prazo definido; não é bloqueio desta Topic.
- Confirmar, nas perguntas do caso da Carolina, se a expansão por páginas adjacentes melhora a resposta e a correção das citações sem exceder o orçamento de contexto.
- **Resolvida em 2026-09-26**: higiene do `.env` — já está listado em `.gitignore` (linhas 9-10) e `git check-ignore -v .env` confirma. Nenhuma ação pendente.
- **Resolvida em 2026-09-26 (Eduardo)**: a extração por IA roda em todos os documentos, dos dois corpora — não é específica dos 10 PDFs de `case-1-carolina-mmgd/`. O corpus maior da #56 não substitui o gabarito de avaliação (D16 continua restrito aos 10 PDFs); ele serve para popular o dataset, dar robustez às métricas de busca, e é candidato a novos casos de teste futuros. A IA copia o texto do PDF para Markdown (nunca resume com palavras próprias) e remove anexos inteiros (vistoria, laudo técnico), contrato social e assinaturas (ver [[d14-data-operations-modeling]] para a decisão completa da etapa e sua posição no pipeline).
- **Resolvida em 2026-09-26**: criada a issue #57 (`resolver: perspec-me`, concerns `d1-source`/`u4-visualization`) para "expor o link direto do documento a partir do .json de cada processo na interface" — fora do escopo de M1/D14, autorizada por Eduardo, vinculada como sub-issue do map #1.

## Evidence

- `hackathon/scripts/check_aws_capabilities.out` — disponibilidade e autorização dos modelos na conta.
- `hackathon/data/case-1-carolina-mmgd/` — 10 PDFs reais usados para caracterizar o corpus.
- `hackathon/ai/app/routes/index.py` e `hackathon/ai/app/routes/search.py` — adapters atuais sem chunking ou embeddings reais.
- AWS, `Amazon Titan Text Embeddings models` e `Amazon Titan Embeddings G1 - Text` — limite de entrada, segmentação lógica recomendada, dimensões e normalização configuráveis.
- Tentativa de `InvokeModel` de 2026-09-22 — `ExpiredTokenException`, sem vetor retornado.
- GitHub issue #29 — Unblocking task com checklist de acesso pessoal, privilégio mínimo, armazenamento local de credenciais, controle de custo e teste funcional.
- Validação da conta pessoal em 2026-09-22 — identidade e disponibilidade do modelo confirmadas; `InvokeModel` recusado no nível da conta com `Error 002`. Evidência registrada no comentário da task #29.
- Última tentativa de `InvokeModel`, 2026-09-22 — mesma configuração e mesmo `Error 002`; definições confirmadas foram registradas em `Decisions so far` do Map #1. Como a task #29 foi fechada, o Topic aberto e atribuído fica fora da Frontier e de Blocked.
- Invocação funcional de `amazon.titan-embed-text-v2:0`, 2026-09-26, `us-east-1`, credenciais em `.env` (conta `640205779371`, role `WSParticipantRole/Participant`) — sucesso: vetor de 1.024 dimensões, norma ≈ 1,0, `inputTextTokenCount=42`, sem erro. Comando e resposta não expuseram credenciais; o vetor bruto não foi persistido no repositório.
- Issue #56 fechada em 2026-09-26 (comentário + close, autorizado por Eduardo) — corpus `hackathon/data/processos aneel/processos/` (5 categorias, ~1.394 PDFs) já estava no commit `6b83a63`; D16 mantém a avaliação restrita aos 10 PDFs de `case-1-carolina-mmgd/`, então esse corpus maior não afeta o gate de `Recall@3` desta Concern.
- `pdftotext` sobre `recurso-48500.004024-2017-80.pdf` e `auto-infracao-48500.004024-2017-80.pdf` (71 e 57 páginas) não encontrou marcadores óbvios de anexo isolado (procuração, laudo técnico como seção própria) por busca de palavra-chave — verificação rápida, não conclusiva; a extensão das páginas pode ser argumentação jurídica extensa, não necessariamente anexo irrelevante, nestes dois PDFs específicos.

## Topic history

- issue-13: selecionou e persistiu no Map o baseline Titan V2/1.024/normalizado, chunking estrutural e expansão por páginas com avaliação pré/pós-expansão separada. Permanece parcial, aberto e atribuído; a task #29 foi fechada, mas a validação funcional, a calibração e o gate de recuperação seguiam pendentes porque a conta ainda recusava `InvokeModel` com `Error 002`.
- issue-13 (2026-09-26): com novas credenciais em `.env`, a invocação funcional do Titan V2 foi confirmada pela primeira vez (1.024 dims, normalizada, sem erro). O baseline de modelo deixa de estar bloqueado por acesso.
- issue-13 (2026-09-26): Eduardo travou o modelo em Titan V2 e adiou a execução do gate `Recall@3`; fechou a #56 (corpus maior, fora do gabarito de avaliação). Permanece `partial` porque surgiu uma nova questão — filtrar conteúdo irrelevante (anexos) antes do chunking/embedding — ainda sem critério definido.
