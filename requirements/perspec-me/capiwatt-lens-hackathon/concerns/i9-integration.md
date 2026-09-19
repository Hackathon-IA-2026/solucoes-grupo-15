---
concern_id: i9-integration
concern: ~/.claude/skills/perspec-me/catalog/concerns/i9-integration/README.md
perspective: infrastructure
status: partial
topics:
  - issue-2 — Qual é o contrato da interface do serviço vetorial (indexar, buscar, agrupar versões) que isola o Bedrock do resto do backend?
  - issue-3 — Como uma família de versões de um documento é identificada e agrupada num único objeto, na ingestão e no resultado da busca?
  - issue-4 — Como as relações entre documentos são representadas (arestas, origem: metadado explícito vs. similaridade) e onde ficam armazenadas?
  - issue-15 — O backend (F3) deve ser dono também do armazenamento documental, junto das arestas, para que grafo e leitura de documentos não atravessem HTTP, dado um corpus da ordem de 100 documentos?
  - issue-7 — Como a entrega de e-mail via SES lida com frequência e deduplicação?
updated_at: 2026-09-18
---

## Current resolution

**Entrega de notificações por e-mail (issue-7, Eduardo, 2026-09-18):** a segunda integração externa do `backend` — depois do serviço vetorial — é o port `Mailer`, e a pergunta original ("via SES") foi reformulada porque a conta do hackathon não tem SES ([[i2-model-serving]], issue-8): o que se especifica é a **entrega de notificação por e-mail atrás do port `Mailer`, independente do adapter** (prévia no 1º ciclo, SES depois). **Frequência e deduplicação são política do `backend`, aplicadas antes do port**: o adapter recebe mensagens já deduplicadas e agregadas e só as entrega de forma idempotente, de modo que prévia e SES se comportem igual. Deduplicação por registro `notification` único em `(user_id, document_version_id)` com `reasons[]` acumulados (família seguida e correlata no escopo ampla colapsam num só registro; `reindex` não re-notifica). Frequência: página inicial imediata; e-mail = **um digest por (usuário, job de ingestão)** — sem agendamento/cron neste ciclo. Contrato `Mailer.send(email_id, to, subject, body) → DeliveryReport`, idempotente por `email_id` (= id do digest). Eventos de observação em [[i6-telemetry]].

**Revisão (issue-15, Eduardo, 2026-09-18):** o port continua sendo a fronteira `backend` → `ai`, em duas camadas (interface em processo no `ai` + HTTP `/internal/v1/*`), e o `backend` continua sem importar `ai`. O que muda é **o que atravessa**: o `ai` deixa de ser dono do armazenamento documental ([[i4-storage]]), então `get_document` **sai do port** — a leitura de documento e a montagem do grafo são locais ao backend. O port fica com `index`, `search`, `similar_families`, `delete`/`reindex` e `reassign_family`; `index` recebe do backend os `document_version`s com `family_id`, metadados e **localizador do original** (não o conteúdo inline), extrai o texto, escreve-o num localizador e devolve no `IndexReport`, por versão, `extracted_text_locator` + `references`. HTTP fica só onde é inerente: uma chamada por busca do usuário e uma por job de ingestão — o esboço original do plano (linhas 132–133).

---

O serviço vetorial é um **port** (interface) do backend, com implementação (adapter) trocável. O port fala em **famílias de documento e versões**, nunca em "coisas do Bedrock": o resto do backend não conhece embeddings, índice nem SDK da AWS. Três operações:

- `index(corpus_version, documents[]) → IndexReport` — cada documento traz `document_id`, `document_version`, `family_id`, conteúdo (texto/chunks) e metadados. Idempotente por `(document_version, model_version)`.
- `search(query, filters, top_k, as_of?) → SearchResult` — devolve hits **já agrupados por `family_id`**: cada hit é uma família com a versão de melhor correspondência e os chunks que casaram (`chunk_id`, `excerpt`, localizador, score); o envelope carrega `corpus_version` e `model_version`.
- `delete(document_version)` / `reindex(corpus_version)` — obrigatórias porque trocar o modelo de embeddings exige reindexar; vetores de modelos diferentes nunca se misturam.

O agrupamento por família é **obrigação do contrato do serviço**, não do backend nem do frontend (decisão de Eduardo, 2026-09-18). O serviço também **é dono do armazenamento dos documentos** (originais e texto extraído) — ver [[i4-storage]].

**Forma do boundary (duas camadas, decisão de Eduardo, 2026-09-18):** o port é uma interface Python dentro do módulo `ai` (`VectorService`: `index`, `search`, `get_document`, `delete`, `reindex`), com adapters `BedrockEmbedder`, `OpenSearchStore` e `DocumentStore`; o módulo `ai` serve esse mesmo port por HTTP em `/internal/v1/{index,search,documents/{id}}`, e isso é a única coisa que o `backend` chama, via um cliente HTTP fino tipado com os mesmos nomes de operação. Um único ponto de troca (onde o código Bedrock vive), não dois.

Quarta operação: `get_document(document_id, version) → DocumentVersion` — metadados + texto extraído + localizador/URL do original (não os bytes); o backend a proxia em `GET /v1/documents/{id}?version=`.

A integração de e-mail está resolvida acima (issue-7); o adapter SES concreto só se especifica quando existir conta com SES.

## Confirmed facts

- Reunião 2026-09-17: arquitetura limpa; interface do serviço vetorial separada da implementação Bedrock para troca futura; Bedrock para busca vetorial desde o início.
- Plano (linha 60): o navegador nunca fala com Bedrock nem com o banco vetorial; F3 chama F2 pelo contrato de IA.
- Plano (linhas 128–133): já existia um esboço F3→F2 (`POST /internal/v1/search`, `POST /internal/v1/ingest`).

## Decisions

- 2026-09-18 (issue-7): frequência e deduplicação de notificações são política do `backend`, aplicadas **antes** do port `Mailer`; nenhum adapter (prévia, SES) decide o que enviar — só entrega, idempotentemente.
- 2026-09-18 (issue-7): chave de deduplicação = `(user_id, document_version_id)`, restrição única no Postgres; motivos múltiplos acumulam em `reasons[]` no mesmo registro.
- 2026-09-18 (issue-7): unidade de frequência do e-mail = um digest por `(user_id, ingestion_job_id)`; a página inicial mostra cada notificação imediatamente. Frequência configurável pelo usuário (`PUT /v1/interests`) fica para a evolução.
- 2026-09-18 (issue-7): a pergunta "via SES" é reformulada como "atrás do port `Mailer`, independente do adapter" — o título da issue não foi editado (sem autorização para isso).

- 2026-09-18 (issue-15): `get_document` sai do port; o backend lê documentos do próprio catálogo. **Supersede** a decisão de issue-2 que a acrescentou e o proxy `GET /v1/documents/{id}` → `/internal/v1/documents/{id}`.
- 2026-09-18 (issue-15): `index` passa a receber localizadores de originais e devolver `extracted_text_locator` por versão; o `ai` nunca devolve texto extraído inline.
- 2026-09-18 (issue-15): rejeitada a variante de merger total (backend chamando o port em processo, um só deployable) — desfaria a separação F2/F3 e a decisão de issue-2.

- 2026-09-18 (issue-2): o port tem três operações — `index`, `search`, `delete`/`reindex` — com granularidade de versão de documento e resultados por família.
- 2026-09-18 (issue-2): o agrupamento de versões nos resultados é parte do contrato do serviço; o consumidor recebe famílias, não chunks soltos.
- 2026-09-18 (issue-2): o serviço vetorial é dono também do armazenamento de documentos (originais + texto extraído), não só dos vetores.
- 2026-09-18 (issue-2): boundary em duas camadas — port `VectorService` em processo no `ai`, exposto ao `backend` só por HTTP `/internal/v1/*`.
- 2026-09-18 (issue-2): o port ganha `get_document(document_id, version)` devolvendo metadados + texto extraído + ponteiro para o original.

## Derived requirements and constraints

- 2026-09-18 (issue-7): tabela `notification` no catálogo do backend com `UNIQUE (user_id, document_version_id)`, `reasons[]` (família seguida / correlato `confirmed` / correlato `suggested`, com `relation_type`), `scope_effective`, `ingestion_job_id`, `created_at`; `reindex(corpus_version)` não cria registros novos para versões já notificadas.
- 2026-09-18 (issue-7): tabela `email_digest` com `email_id` (chave), `user_id`, `ingestion_job_id`, `notification_ids[]`, `delivery_status`, `provider_message_id?`; um digest por `(user_id, ingestion_job_id)`, gerado ao fim do job.
- 2026-09-18 (issue-7): port `Mailer.send(email_id, to, subject, body) → DeliveryReport`, idempotente por `email_id`. Adapter de prévia: grava/sobrescreve um arquivo por `email_id` no volume e expõe na página inicial. Adapter SES (futuro): guarda o `MessageId` do SES e não reenvia se já houver um para o `email_id`.
- 2026-09-18 (issue-7): restrição herdada pelo adapter SES futuro — conta nova de SES nasce em sandbox (só identidades verificadas); destinatário não verificado deve falhar de forma explícita e registrada em `DeliveryReport`/telemetria, nunca silenciosa.
- 2026-09-18 (issue-7): os testes de contrato do `Mailer` rodam contra o adapter de prévia (sempre) e, quando existir, contra o SES — mesma regra dos adapters do serviço vetorial.

- 2026-09-18 (issue-15): rota `/internal/v1/documents/{id}` deixa de existir; `/internal/v1/documents/{id}/family` (`reassign_family`) e `/internal/v1/families/{id}/similar` permanecem.
- 2026-09-18 (issue-15): `IndexReport` por versão: `{document_version, extracted_text_locator, references[], chunks_indexed}`.
- 2026-09-18 (issue-15): o `ai` precisa de acesso de leitura ao storage de originais e de escrita ao de texto extraído (mesmo volume local / bucket S3 do backend) — detalhe físico na issue #8.

- Nenhum tipo do SDK do Bedrock/OpenSearch atravessa o port; o backend depende só da interface.
- Toda resposta de `search` carrega `corpus_version` e `model_version` (reprodutibilidade — [[i7-reproducibility]], issue #9).
- `index` idempotente por `(document_version, model_version)`; `reindex(corpus_version)` existe desde o primeiro ciclo.
- O que define `family_id` é decisão da issue #3; este contrato só exige que exista e que o adapter agrupe por ele.
- 2026-09-18 (issue-3): o port ganha `reassign_family(document_version, family_id)` — move uma versão (e seus chunks/vetores) para outra família sem reembedding; usada pelo `backend` ao aceitar uma sugestão de fusão ([[d4-data-dictionary]]). Exposta em `/internal/v1/documents/{id}/family`.
- 2026-09-18 (issue-3): o hit por família em `search` carrega a **versão mais recente** da família como face e os chunks casados cada um com sua `document_version` — refina o "versão de melhor correspondência + chunks" da issue-2 (ver [[u4-visualization]], [[d4-data-dictionary]]).
- 2026-09-18 (issue-4): o resultado de `index` passa a incluir `references: [{identifier_raw, relation_type?, locator}]` (referências explícitas encontradas no texto) e o port ganha `similar_families(family_id, top_k) → [{family_id, score}]`. O serviço só entrega **candidatos**; resolução de alvo, gravação e curadoria das arestas são do `backend` ([[i4-storage]], [[i10-hybrid-decision-intelligence]]). `similar_families` exposta em `/internal/v1/families/{id}/similar`.
- Testes de contrato do port rodam contra o adapter Bedrock e contra um adapter fake/local (regra "contrato interno continua igual ao trocar Demo API pelo mecanismo real", plano linha 144).
- O cliente HTTP do `backend` é gerado/tipado a partir dos tipos do port; os mesmos testes de contrato rodam contra o fake em processo e contra a superfície HTTP do `ai`.
- O `backend` nunca importa o módulo `ai` diretamente — só o cliente HTTP.

## Open questions

- (issue-7) Se a ingestão virar contínua (Fog "ingestão contínua a partir de ANEEL/SEI"), "um digest por job" degenera em "um e-mail por documento"; a unidade de agregação passa a ser por período — a chave de dedup e o lugar da política não mudam.
- (issue-7) Especificação concreta do adapter SES (região, identidade remetente, saída do sandbox) — só quando houver conta com SES.

## Evidence

- (issue-7) Plano l.50, 86, 112, 191: F3 é dono da entrega e da deduplicação de e-mails, "prévia local, depois envio controlado; inclui frequência e deduplicação"; aceite = "frequência aplicada e sem duplicação no cenário testado". Plano l.114: a ingestão devolve um id de job. Plano l.134: `PUT /v1/interests` com frequência é evolução.
- (issue-7) `hackathon/scripts/check_aws_capabilities.out` l.317–334: SES negado na conta do hackathon; observação do script sobre sandbox de SES.
- (issue-7) Comentário de resolução da issue #6: eventos base de notificação e o encaminhamento explícito da frequência/dedup para a #7.
- Map issue #1, Notes (decisões de 2026-09-17).
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 60, 102, 118, 128–133, 144, 154–162.

## Topic history

- issue-7: especificou a entrega de e-mail atrás do port `Mailer` (política de frequência/dedup no backend, antes do port; dedup por `(user_id, document_version_id)`; digest por `(usuário, job)`; `send` idempotente por `email_id`); reformulou "via SES" como independente de adapter.
- issue-15: tirou `get_document` do port e fez `index` trabalhar por localizadores (entrada: original; saída: texto extraído); HTTP restrito a `search`, `index`, `similar_families`, `reassign_family`, `delete`/`reindex`.

- issue-4: acrescentou `references` ao resultado de `index` e a operação `similar_families` ao port; manteve o serviço vetorial como fonte de candidatos, não dono das relações.
- issue-3: refinou a forma do hit por família em `search` (face = versão mais recente; chunks etiquetados por versão) e acrescentou a operação `reassign_family` ao port.
- issue-2: fixou as operações do port (`index`, `search`, `get_document`, `delete`/`reindex`), granularidade por versão/família, agrupamento como obrigação do serviço, o serviço como dono do armazenamento de documentos, e o boundary em duas camadas (port em processo no `ai` + HTTP `/internal/v1/*` para o `backend`).
