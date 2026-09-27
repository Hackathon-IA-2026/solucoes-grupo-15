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
  - issue-28 — Como a busca pagina resultados ordenados por relevância em lotes de 10 sem alterar a ordem entre páginas?
  - issue-64 — Ao remover o conceito de família de documentos, como versões e documentos passam a ser identificados, agrupados e exibidos na ingestão, busca e interface?
  - issue-96 — Como um hit de busca identifica de forma estável o chunk casado, para feedback e evidence_refs?
  - issue-92 — Qual é a forma concreta de `similar_families` e de `references[]` no `IndexReport`, e como o backend transforma esses candidatos em arestas de `document_relations`?
  - issue-95 — `index` recebe o localizador do original (e o `ai` extrai o texto) ou o Markdown já extraído inline?
  - issue-98 — `delete(document_version)` do port é exposto como rota no `ai` ou sai do contrato?
updated_at: 2026-09-27
---

## Current resolution

**Autoridade de disponibilidade (Eduardo, 2026-09-20):** [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md) prevalece sobre hipóteses do plano e diagnósticos anteriores quanto a serviços, regiões e permissões. Diagnósticos datados permanecem evidência histórica; disponibilidade não equivale à validação funcional do fluxo da aplicação.

**Revisão da issue-7 (2026-09-20, aceita por Eduardo):** SES não está no inventário; manter prévia local e o contrato `Mailer`, com frequência/deduplicação no backend. SNS está disponível, mas não foi adotado. A revisão corrige disponibilidade e consolida a especificação sem alterar esse comportamento.

**Entrega de notificações por e-mail (issue-7, Eduardo, 2026-09-18):** a segunda integração externa do `backend` — depois do serviço vetorial — é o port `Mailer`, e a pergunta original ("via SES") foi reformulada porque a conta do hackathon não tem SES ([[i2-model-serving]], issue-8): o que se especifica é a **entrega de notificação por e-mail atrás do port `Mailer`, independente do adapter** (prévia no 1º ciclo, SES depois). **Frequência e deduplicação são política do `backend`, aplicadas antes do port**: o adapter recebe mensagens já deduplicadas e agregadas e só as entrega de forma idempotente, de modo que prévia e SES se comportem igual. Deduplicação por registro `notification` único em `(user_id, document_version_id)` com `reasons[]` acumulados (família gatilho e correlata no escopo ampla colapsam num só registro; `reindex` não re-notifica). Frequência: página inicial imediata; e-mail = **um digest por (usuário, job de ingestão)** — sem agendamento/cron neste ciclo. Contrato `Mailer.send(email_id, to, subject, body) → DeliveryReport`, idempotente por `email_id` (= id do digest). Eventos de observação em [[i6-telemetry]].

**⚠️ E-mail: implementado mas não ativado (out of scope operacional).** O código do port `Mailer` e do adapter `PreviewMailer` (`app/mailer.py`) está completo e testado, incluindo o modelo `EmailDigest`, a rota `GET /v1/users/{user_id}/email-digests` e os eventos de telemetria (`email_digest_generated`, `notification_delivered_email`). No entanto, o canal de e-mail **não é usado operacionalmente** neste ciclo porque o SES não foi disponibilizado pela organização do hackathon (issue #8, [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md)). A entrega de notificações acontece **apenas pela home** (`notification_delivered_home`). O código permanece como evidência do trabalho realizado e está pronto para ser ativado se o SES for liberado futuramente.

**Revisão (issue-15, Eduardo, 2026-09-18):** o port continua sendo a fronteira `backend` → `ai`, em duas camadas (interface em processo no `ai` + HTTP `/internal/v1/*`), e o `backend` continua sem importar `ai`. O que muda é **o que atravessa**: o `ai` deixa de ser dono do armazenamento documental ([[i4-storage]]), então `get_document` **sai do port** — a leitura de documento e a montagem do grafo são locais ao backend. O port fica com `index`, `search`, `similar_families`, `delete`/`reindex` e `reassign_family`; ~~`index` recebe do backend os `document_version`s com `family_id`, metadados e **localizador do original** (não o conteúdo inline), extrai o texto,~~ **Superado pela issue-95:** `index` recebe o Markdown já extraído inline (ver a revisão da issue-95 abaixo). Continua valendo que o `ai` escreve o texto num localizador e devolve no `IndexReport`, por versão, `extracted_text_locator` + `references`. HTTP fica só onde é inerente: uma chamada por busca do usuário e uma por job de ingestão — o esboço original do plano (linhas 132–133).

**Revisão (issue-98, 2026-09-27): `delete(document_version)` exposto no `ai`.** A suíte e2e da #88 mostrou que o port listava `delete(document_version)` sem rota: remover uma versão só acontecia como efeito colateral de `reindex`. O dono do repo decidiu expor a operação. Forma vigente:

- **Rota.** `DELETE /internal/v1/documents/{document_version}` → `{document_version, model_version, chunks_deleted}`. O path segue a convenção de `reassign_family` (`/internal/v1/documents/{id}/family`). Não reintroduz o `GET /internal/v1/documents/{id}` (`get_document`), que a issue-15 tirou do port.
- **Pipeline real** (`EMBEDDER=bedrock`/`cached`): remove do índice OpenSearch do `model_version` corrente todos os chunks da versão. `chunks_deleted` é quantos havia. O `ai` também grava um tombstone da versão nos vetores brutos ([[i7-reproducibility]]) e esquece o `IndexReport` cacheado. Depois disso, a busca e `similar_families` deixam de ver a versão, o reindex offline a partir dos vetores brutos não a ressuscita, e um `index` seguinte da mesma versão grava os chunks de novo em vez de devolver o relatório antigo.
- **Modo fixture** (`EMBEDDER=fake`): não há índice vetorial. O `ai` esquece o `IndexReport` cacheado da versão e devolve em `chunks_deleted` o `chunks_indexed` que ela tinha. A busca fixture é declarativa e não muda.
- **Idempotente.** Uma versão desconhecida ou já apagada devolve 200 com `chunks_deleted: 0`, nunca 404, para que um retry do `backend` não vire erro.
- **O texto em `extracted_text_locator` não é apagado.** Ele está registrado no catálogo do `backend`, que é dono do ciclo de vida da versão ([[i4-storage]]), e é o que a página do documento lê. `delete` só mexe no derivado: índice e vetores brutos.
- **Vetores brutos.** A remoção é lógica. O arquivo é append-only, então as linhas antigas continuam no disco, mas o replay as descarta.
- **Sem rota pública no `backend`.** O `backend` ainda não chama `delete` (não há `AiClient.delete`) e não mexe no catálogo, em `document_relations` nem nas listas congeladas de `SearchExecution` quando uma versão sai do índice. Ver Open questions.

**Revisão (issue-95, 2026-09-27): `index` recebe o Markdown já extraído, inline.** A suíte e2e da #88 mostrou que o contrato (issue-15: "`index` recebe localizador do original, o `ai` extrai o texto") não batia com a implementação. O dono do repo decidiu atualizar o contrato para o comportamento real, sem mudar o código. A extração PDF/HTML → Markdown ([[d14-data-operations-modeling]]) é uma **etapa anterior à fronteira**, feita pelo pipeline de extração: a #59 para o caso 1, levada ao corpus completo em lote pela #68 (contrato em `requirements/contracts/extraction-route.md`). O `ai` não lê originais e não faz OCR nem parsing de PDF. Forma vigente:

- **Entrada.** `POST /internal/v1/index` recebe `{documents: [{document_version, text, family_id?, corpus_version?}]}`. `text` é o Markdown completo da versão, já extraído. No cliente do `backend` esse tipo é o `IndexDocumentPayload`. `family_id` e `corpus_version` são opcionais no schema, mas obrigatórios no pipeline real (`EMBEDDER=bedrock` ou `cached`): se um dos dois faltar, a resposta é 422. O adapter fixture ignora os dois. `corpus_version` vai **por documento**, não como argumento do lote: a assinatura `index(corpus_version, documents[])` é conceitual.
- **O que o `ai` faz.** Faz o chunking estrutural e os embeddings sobre esse `text`, grava os chunks no índice e **grava o texto recebido, sem alterar, em `<DOCUMENTS_DIR>/<document_version>/extracted.txt`**. O caminho desse arquivo volta como `extracted_text_locator`, e o `backend` o registra em `DocumentVersion.extracted_text_locator`. A página do documento lê esse arquivo.
- **Saída.** Um `IndexReport` por versão: `{document_version, extracted_text_locator, chunks_indexed, model_version, total_input_tokens, references[]}`. `total_input_tokens` é `null` no modo fixture. `references[]` segue a forma da issue-92 e vem vazio no modo fixture. O texto nunca volta inline no `IndexReport`: essa parte da issue-15 continua valendo.
- **`reindex`.** `POST /internal/v1/reindex` usa a mesma forma. O `backend` reenvia o texto de cada versão, e o `ai` nunca lê o catálogo.
- **De onde o `backend` tira o texto hoje.** Na ingestão `case1-real`, o `backend` lê o Markdown da #59 versionado em `hackathon/data/case-1-carolina-mmgd/<processo>/<peca>.md` (ou em `CASE_DOCUMENTS_DIR`). Na ingestão demo, envia os resumos curtos da fixture `demo_corpus.json`. A ingestão ainda não lê a saída em lote da #68 (`hackathon/.pipeline-output/`): ver Open questions.

**Revisão (issue-92, 2026-09-27): `similar_families` e `references[]` implementados.** A suíte e2e da #88 mostrou que nenhuma das duas operações de candidatos de aresta existia (404; `IndexReport` sem `references`). Formas concretas, sem mudar a divisão de posse: (1) `GET /internal/v1/families/{family_id}/similar?top_k=3` devolve `{family_id, model_version, similar: [{family_id, score}]}`. O vetor de família é a média renormalizada dos embeddings de todos os chunks da família no índice, a mesma agregação calibrada nas issues #61/#74, e o score é o produto interno. A própria família nunca aparece, e uma família sem chunks no índice dá 404. No modo fixture não há vetores, então a resposta é `similar: []`. (2) Cada `IndexReport` carrega `references: [{identifier_raw, relation_type, locator}]`, com `locator` = `chunk_id` (issue-96) do chunk onde a citação foi achada. O reconhecedor é deliberadamente estreito: só "Auto de Infração [– AI –] nº N/AAAA[-SIGLA]", sempre com `relation_type: null`. No modo fixture a lista é vazia. O `backend` resolve e grava no fim do job de ingestão: ver [[d14-data-operations-modeling]] (limiares) e [[i4-storage]] (`document_relations.score`).

**Revisão (issue-96, 2026-09-27): cada hit identifica o chunk de forma estável.** A suíte e2e da #88 mostrou que os hits de `search` não traziam identificador de chunk e que o `chunk_index` do `backend` era a posição do hit na lista do `ai` — que muda de consulta para consulta. Agora cada hit de `/internal/v1/search` carrega `chunk_id` (id do chunk no índice, `"<document_version>#chunk-NNNN"`) e `chunk_index` (índice real do chunk dentro do documento, 0-based, já resolvido pelo `ai`, que é dono do formato do `chunk_id`). O `backend` repassa os dois em cada resultado de `POST /v1/search`, persiste-os nos hits crus do `SearchExecution` e usa o `chunk_index` real no desempate final da ordem total `(-score, document_version, chunk_index)`. Com isso, `(document_version, chunk_index)` — a chave de chunk do feedback ([[i6-telemetry]], issue #82) — e os `evidence_refs` da #66 apontam para um chunk estável, que é o mesmo em qualquer consulta e em qualquer reindex do mesmo `model_version`.

**Revisão (issue-64, Eduardo, 2026-09-26): a unidade de paginação passa a ser o chunk casado.** A busca deixou de agrupar ou deduplicar por família na visualização ([[u4-visualization]], [[d11-consistency]]); sem agrupamento, não há mais uma coleção de tamanho variável (chunks por família) para colapsar antes de paginar, então o `offset`/`cursor` pode incidir direto sobre a lista de hits crus que o `ai` já devolve. Isto supersede as duas seções abaixo ("unidade de paginação é a família" e o desempate por `family_id`) — o restante do mecanismo de congelamento (ordenação fixada na primeira chamada, `cursor` opaco, `total` exato) continua válido, só a unidade muda.

**Paginação lazy (issue-28, Eduardo, 2026-09-25).** A busca entrega **lotes de 10 famílias**, carregados sob demanda, sempre na mesma ordenação global.

~~A unidade de paginação é a **família**, nunca o chunk. Um `offset` sobre chunks não corresponde a um `offset` sobre famílias, porque o agrupamento colapsa um número variável de chunks em cada família. Paginar por chunk quebraria o invariante de [[d11-consistency]] ("cada família no máximo uma vez por consulta") na fronteira entre lotes.~~ **Superado pela issue-64:** a unidade de paginação é o **chunk casado**; o invariante que isso protegia (não dividir uma família entre lotes) deixou de existir junto com o dedup por família.

A ordenação é **congelada na primeira chamada**, não recalculada a cada lote. A primeira chamada resolve a busca inteira e persiste a lista ordenada de hits (chunk casado, cada um com `document_version`) no `SearchExecution` que a issue-9 já exige ([[i7-reproducibility]], [[m10-versioning]]). O `request_id` dessa execução é a identidade do conjunto congelado. Recalcular o ranking a cada lote permitiria que um hit já exibido saísse do lugar, ou sumisse, entre a página 1 e a 2.

Contrato: `POST /v1/search` aceita `cursor?` e `limit` (padrão 10) e devolve `next_cursor?` e `total`. O `cursor` é opaco e codifica `(request_id, posição)`. **Continuações não chamam o `ai`**: a primeira chamada por consulta é a única, como [[i2-model-serving]] e o esboço do plano já exigiam ("uma chamada por busca do usuário"). O lote seguinte é servido da lista congelada mais a hidratação do catálogo ([[i4-storage]]).

`total` é conhecido e exato desde o primeiro lote, porque o conjunto congelado é completo. A interface não precisa estimar ([[u4-visualization]]).

**Empate e ordem total.** A ordenação precisa ser uma ordem *total*, não parcial: score decrescente e, no empate, ~~`family_id` crescente~~ **um campo de desempate ainda a definir pela issue-64** (ver Open questions — candidatos são `document_version` ou `chunk_id`, agora que a unidade é o chunk). Sem o desempate determinístico, duas execuções da mesma consulta podem intercalar empatados de forma diferente e a paginação deixa de ser reproduzível. O desempate é parte de `ranking_version` ([[m10-versioning]], que já o inclui: "código e configuração da recuperação, filtros, pesos, agrupamento e desempate").

**Índice atualizado no meio da navegação.** O disparo de ingestão é contínuo ([[u3-frequency]]: qualquer documento novo), então o corpus pode mudar entre dois lotes. O conjunto congelado pertence ao `corpus_version` da primeira chamada e continua sendo servido dele até o fim da navegação — a ordem nunca muda debaixo do usuário. Quando existir `corpus_version` mais recente, a resposta marca `stale_corpus: true`; a interface oferece refazer a busca, e nunca mistura corpora no mesmo conjunto de resultados. "Mais recente" quer dizer **da última ingestão** (issue-97): o `backend` grava em cada `DocumentVersion` o instante da ingestão que a escreveu (`ingested_at`, um valor por job) e toma como atual o `corpus_version` da linha com o maior `ingested_at`. `corpus_version` é o hash do manifesto (issue-68) e não tem ordem própria; comparar por ordem lexicográfica marcaria como atual o hash "maior", não o último.

**O gate de recuperação não muda.** `Recall@3` é medido sobre os três primeiros processos distintos ([[m5-performance-metrics]]), que estão sempre dentro do primeiro lote de 10. A paginação não desloca a métrica nem o gate `2/3`.

**Lado do agrupamento (decisão de Eduardo, 2026-09-25): o agrupamento por família fica no `backend`.** Isto **supersede** a decisão da issue-2 registrada abaixo ("o agrupamento por família é obrigação do contrato do serviço"), e confirma o que o código já faz (`hackathon/backend/app/routes/search.py`; o `ai` devolve hits crus).

Consequências:

- `search` no port devolve **hits crus por chunk**, cada um com `family_id`, `document_version`, `chunk_id`/`chunk_index` (issue-96), `excerpt`, localizador e score. Não devolve famílias.
- O `backend` agrupa por `family_id`, escolhe a face, monta `matched_chunks` e só então **congela** a lista ordenada. O congelamento acontece depois do agrupamento, no mesmo lado — é o que torna o cursor coerente com o invariante de uma família por consulta.
- O invariante "cada família no máximo uma vez por consulta" passa a ser obrigação da resposta do `backend`, não do `SearchResult` do `ai` ([[d11-consistency]]).
- O `ai` continua dono do ranking e da ordem dos hits crus; o `backend` **nunca reordena** por score, só colapsa preservando a ordem de primeira ocorrência. Trocar o adapter vetorial continua não tocando no `backend`.

O que segue foi a resolução da issue-2 e permanece válido onde não contradiz o acima: o port como interface trocável, o vocabulário de famílias e versões, a idempotência de `index`, o agrupamento por família como obrigação do serviço e o boundary em duas camadas. Ficam **superados** pela issue-15 a posse do armazenamento documental pelo `ai`, a operação `get_document` com seu proxy, a rota `/internal/v1/documents/{id}` e o adapter `DocumentStore`. Fica **superada** pela issue-3 a face do hit em `search`: é a versão mais recente da família, não a de melhor correspondência.

---

O serviço vetorial é um **port** (interface) do backend, com implementação (adapter) trocável. O port fala em **famílias de documento e versões**, nunca em "coisas do Bedrock": o resto do backend não conhece embeddings, índice nem SDK da AWS. Três operações:

- `index(corpus_version, documents[]) → IndexReport` — cada documento traz `document_id`, `document_version`, `family_id`, conteúdo (texto/chunks) e metadados. Idempotente por `(document_version, model_version)`.
- `search(query, filters, top_k, as_of?) → SearchResult` — devolve hits **já agrupados por `family_id`**: cada hit é uma família com ~~a versão de melhor correspondência~~ → **a versão mais recente da família** (corrigido pela issue-3; ver Derived requirements e [[u4-visualization]]) e os chunks que casaram (`chunk_id`, `excerpt`, localizador, score); o envelope carrega `corpus_version` e `model_version`.
- `delete(document_version)` / `reindex(corpus_version)` — obrigatórias porque trocar o modelo de embeddings exige reindexar; vetores de modelos diferentes nunca se misturam.

~~O agrupamento por família é **obrigação do contrato do serviço**, não do backend nem do frontend (decisão de Eduardo, 2026-09-18).~~ **Superado pela issue-28 (2026-09-25):** o agrupamento fica no `backend`; o `ai` devolve hits crus — ver acima. ~~O serviço também é dono do armazenamento dos documentos (originais e texto extraído).~~ **Superado pela issue-15:** o backend é dono do catálogo documental; o `ai` é dono só do índice derivado — ver [[i4-storage]].

**Forma do boundary (duas camadas, decisão de Eduardo, 2026-09-18):** o port é uma interface Python dentro do módulo `ai`, com adapters `BedrockEmbedder` e `OpenSearchStore`; o módulo `ai` serve esse mesmo port por HTTP em `/internal/v1/*`, e isso é a única coisa que o `backend` chama, via um cliente HTTP fino tipado com os mesmos nomes de operação. Um único ponto de troca (onde o código Bedrock vive), não dois.

Composição vigente do `VectorService`, depois das issues #3, #4 e #15:

| Operação | Rota `/internal/v1/*` | Origem |
|---|---|---|
| `index` | `/internal/v1/index` | issue-2 (entrada: Markdown já extraído, inline, desde a issue-95; a entrada por localizador da issue-15 foi superada) |
| `search` | `/internal/v1/search` | issue-2 |
| `delete` | `DELETE /internal/v1/documents/{document_version}` | issue-2 (rota na issue-98) |
| `reindex` | `/internal/v1/reindex` | issue-2 (rota na issue #69) |
| `reassign_family` | `/internal/v1/documents/{id}/family` | issue-3 |
| `similar_families` | `/internal/v1/families/{id}/similar` | issue-4 (forma concreta na issue-92) |

**Superados pela issue-15:** a operação `get_document`, o adapter `DocumentStore` e a rota `/internal/v1/documents/{id}`.

~~Quarta operação: `get_document(document_id, version) → DocumentVersion` — metadados + texto extraído + localizador/URL do original (não os bytes); o backend a proxia em `GET /v1/documents/{id}?version=`.~~ **Superado pela issue-15** (ver Decisions): `get_document` saiu do port e o proxy deixou de existir. A rota pública `GET /v1/documents/{id}?version=` continua, servida em processo pelo catálogo do backend ([[i4-storage]]).

A integração de e-mail está resolvida acima (issue-7); o adapter SES concreto só se especifica quando existir conta com SES.

## Confirmed facts

- 2026-09-20 (Eduardo): confirmou o corte local proposto e determinou que o documento AWS é a autoridade para disponibilidade de serviços. Os diagnósticos de 2026-09-18 abaixo são históricos.

- Reunião 2026-09-17: arquitetura limpa; interface do serviço vetorial separada da implementação Bedrock para troca futura; Bedrock para busca vetorial desde o início.
- Plano (linha 60): o navegador nunca fala com Bedrock nem com o banco vetorial; F3 chama F2 pelo contrato de IA.
- Plano (linhas 128–133): já existia um esboço F3→F2 (`POST /internal/v1/search`, `POST /internal/v1/ingest`).

## Decisions

- 2026-09-27 (issue-98, decisão do dono do repo registrada na issue): `delete(document_version)` fica no port e é exposto em `DELETE /internal/v1/documents/{document_version}`. As escolhas abaixo foram do agente, pela opção mais conservadora, e estão pendentes de confirmação: (1) operação idempotente (200 com `chunks_deleted: 0`), sem 404; (2) o texto em `extracted_text_locator` fica; (3) os vetores brutos recebem tombstone (remoção lógica, retenção física); (4) nenhuma rota nem chamada nova no `backend`.
- 2026-09-27 (issue-95, decisão do dono do repo registrada na issue): `index` recebe o Markdown já extraído inline em `documents[].text`. A extração é do pipeline (#59/#68), antes da fronteira, e o `ai` não lê originais. O `ai` grava o texto recebido num localizador e devolve só `extracted_text_locator`, nunca o texto. **Supersede**, da decisão de issue-15, a parte "`index` passa a receber localizadores de originais" e o requisito derivado "o `ai` precisa de acesso de leitura ao storage de originais".
- 2026-09-27 (issue-97): o `corpus_version` "mais recente" que decide `stale_corpus` é o da última ingestão (`DocumentVersion.ingested_at`), nunca o maior em ordem lexicográfica. Decisão do agente pelo critério da própria issue, pendente de confirmação.
- 2026-09-27 (issue-92): `similar_families` responde `{family_id, model_version, similar: [{family_id, score}]}` com `top_k` padrão 3 e vetor de família = média renormalizada dos chunks (agregação da #74); `IndexReport` ganha `references[]` com `locator` = `chunk_id`. O `ai` não aplica limiar nenhum; o `backend` resolve ids, aplica `limiar_relacao`/`limiar_fusao` e grava as arestas ao fim da ingestão.
- 2026-09-27 (issue-96): cada hit de `search` carrega `chunk_id` e `chunk_index` (índice real do chunk no documento, resolvido pelo `ai`); o `backend` usa esse `chunk_index`, nunca a posição do hit na lista, como identidade do chunk (feedback #82, `evidence_refs` #66) e como desempate final da ordem total.
- 2026-09-26 (issue-64, Eduardo): `family_id`, a chave de identificação e `reassign_family` continuam **no contrato do port e no backend** — a #64 não remove nada do contrato, só do que a interface expõe. O atributo de filtro `family_id` em `search`/`index` e a operação `reassign_family` permanecem exatamente como especificados.
- 2026-09-26 (issue-64, Eduardo): a unidade de paginação da busca passa de "família" para **chunk casado** — consequência de a visualização não agrupar nem deduplicar mais por peça ([[u4-visualization]], [[d11-consistency]]). O campo de desempate na ordem total (antes `family_id`) fica em aberto.

- 2026-09-25 (issue-28, Eduardo): o agrupamento por família fica no `backend`; o `ai` devolve hits crus por chunk. **Supersede** a decisão de issue-2 "o agrupamento é obrigação do contrato do serviço". O congelamento do conjunto ordenado acontece depois do agrupamento, no mesmo lado.
- 2026-09-25 (issue-28, Eduardo): a busca entrega lotes de 10 famílias, carregados sob demanda, na mesma ordenação global; a unidade de paginação é a família, nunca o chunk.
- 2026-09-25 (issue-28, Eduardo): a ordenação é congelada na primeira chamada e persistida no `SearchExecution`; o `cursor` é opaco e codifica `(request_id, posição)`; continuações não chamam o `ai`.
- 2026-09-25 (issue-28, Eduardo): ordem total obrigatória — score decrescente, empate por `family_id` crescente; o desempate faz parte de `ranking_version`.
- 2026-09-25 (issue-28, Eduardo): o conjunto congelado pertence ao `corpus_version` da primeira chamada; `corpus_version` mais recente marca `stale_corpus: true` e a interface oferece refazer a busca, sem misturar corpora.

- 2026-09-20 (issue-7, Eduardo): reafirmados digest por usuário/job, deduplicação por usuário/versão e adapter de prévia idempotente; SES apenas futuro condicionado a ambiente com acesso, SNS não selecionado.

- 2026-09-18 (issue-7): frequência e deduplicação de notificações são política do `backend`, aplicadas **antes** do port `Mailer`; nenhum adapter (prévia, SES) decide o que enviar — só entrega, idempotentemente.
- 2026-09-18 (issue-7): chave de deduplicação = `(user_id, document_version_id)`, restrição única no Postgres; motivos múltiplos acumulam em `reasons[]` no mesmo registro.
- 2026-09-18 (issue-7): unidade de frequência do e-mail = um digest por `(user_id, ingestion_job_id)`; a página inicial mostra cada notificação imediatamente. Frequência configurável pelo usuário (`PUT /v1/interests`) fica para a evolução.
- 2026-09-18 (issue-7): a pergunta "via SES" é reformulada como "atrás do port `Mailer`, independente do adapter" — o título da issue não foi editado (sem autorização para isso).

- 2026-09-18 (issue-15): `get_document` sai do port; o backend lê documentos do próprio catálogo. **Supersede** a decisão de issue-2 que a acrescentou e o proxy `GET /v1/documents/{id}` → `/internal/v1/documents/{id}`.
- 2026-09-18 (issue-15): ~~`index` passa a receber localizadores de originais e~~ devolver `extracted_text_locator` por versão; o `ai` nunca devolve texto extraído inline. **Entrada superada pela issue-95:** `index` recebe o Markdown já extraído, inline. A saída continua valendo.
- 2026-09-18 (issue-15): rejeitada a variante de merger total (backend chamando o port em processo, um só deployable) — desfaria a separação F2/F3 e a decisão de issue-2.

- 2026-09-18 (issue-2): o port tem três operações — `index`, `search`, `delete`/`reindex` — com granularidade de versão de documento e resultados por família.
- 2026-09-18 (issue-2): o agrupamento de versões nos resultados é parte do contrato do serviço; o consumidor recebe famílias, não chunks soltos.
- 2026-09-18 (issue-2): o serviço vetorial é dono também do armazenamento de documentos (originais + texto extraído), não só dos vetores.
- 2026-09-18 (issue-2): boundary em duas camadas — port `VectorService` em processo no `ai`, exposto ao `backend` só por HTTP `/internal/v1/*`.
- 2026-09-18 (issue-2): o port ganha `get_document(document_id, version)` devolvendo metadados + texto extraído + ponteiro para o original.

## Derived requirements and constraints

- A prévia deve ser identificada como prévia na interface e no resultado de entrega; o fluxo deste ciclo não depende de SES/SNS.

- 2026-09-18 (issue-7): tabela `notification` no catálogo do backend com `UNIQUE (user_id, document_version_id)`, `reasons[]` (família gatilho / correlato `confirmed` / correlato `suggested`, com `relation_type` — "gatilho", nunca "seguida": a issue-6 rejeitou o filtro por acompanhamento, [[u3-frequency]]), `scope_effective`, `ingestion_job_id`, `created_at`; `reindex(corpus_version)` não cria registros novos para versões já notificadas.
- 2026-09-18 (issue-7): tabela `email_digest` com `email_id` (chave), `user_id`, `ingestion_job_id`, `notification_ids[]`, `delivery_status`, `provider_message_id?`; um digest por `(user_id, ingestion_job_id)`, gerado ao fim do job.
- 2026-09-18 (issue-7): port `Mailer.send(email_id, to, subject, body) → DeliveryReport`, idempotente por `email_id`. Adapter de prévia: grava/sobrescreve um arquivo por `email_id` no volume e expõe na página inicial. Adapter SES (futuro): guarda o `MessageId` do SES e não reenvia se já houver um para o `email_id`.
- 2026-09-18 (issue-7): restrição herdada pelo adapter SES futuro — conta nova de SES nasce em sandbox (só identidades verificadas); destinatário não verificado deve falhar de forma explícita e registrada em `DeliveryReport`/telemetria, nunca silenciosa.
- 2026-09-18 (issue-7): os testes de contrato do `Mailer` rodam contra o adapter de prévia (sempre) e, quando existir, contra o SES — mesma regra dos adapters do serviço vetorial.

- 2026-09-18 (issue-15): rota `/internal/v1/documents/{id}` deixa de existir; `/internal/v1/documents/{id}/family` (`reassign_family`) e `/internal/v1/families/{id}/similar` permanecem.
- 2026-09-18 (issue-15): `IndexReport` por versão: `{document_version, extracted_text_locator, references[], chunks_indexed}`. **Estendido** (issues #69, #73, #92, #95): hoje traz também `model_version` e `total_input_tokens`.
- 2026-09-18 (issue-15): o `ai` precisa ~~de acesso de leitura ao storage de originais e~~ de escrita ao de texto extraído (mesmo volume local / bucket S3 do backend) — detalhe físico na issue #8. **Superado em parte pela issue-95:** o `ai` não lê originais.
- 2026-09-27 (issue-98): `delete(document_version)` age só sobre o derivado do `model_version` corrente: os chunks no índice, os vetores brutos (tombstone) e o cache de idempotência de `index`. É idempotente. Depois de `delete`, `index` da mesma versão tem que reindexar de verdade.
- 2026-09-27 (issue-95): o chunking e os embeddings rodam sobre o `text` recebido em `index`, e o arquivo em `extracted_text_locator` é exatamente esse `text`. Por isso a página do documento, os chunks do índice e os vetores brutos ([[i7-reproducibility]]) derivam do mesmo Markdown.

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

- (issue-98, aberta) Idempotência × 404: o agente escolheu 200 com `chunks_deleted: 0` para versão desconhecida ou já apagada. O 404 foi rejeitado porque transformaria um retry do `backend` em erro. Falta confirmação do dono.
- (issue-98, aberta) Quem apaga o texto em `extracted_text_locator` quando uma versão sai do corpus? Decisão conservadora do agente: `delete` não apaga. O arquivo segue o ciclo de vida da linha `DocumentVersion` do catálogo do `backend`, que hoje não tem fluxo de remoção.
- (issue-98, aberta) Vetores brutos: o tombstone preserva as linhas no disco e não há compactação. Falta decidir se remoção deve ser física, por exemplo por exigência de retenção de dado.
- (issue-98, aberta) O `backend` ainda não chama `delete`. Não há `AiClient.delete` nem fluxo de remoção no catálogo. Quando houver, falta definir o que acontece com a linha `DocumentVersion`, com as arestas de `document_relations` derivadas dos chunks da versão (`similar_a`, `referencia`) e com os conjuntos congelados de `SearchExecution` que a citam.
- (issue-98, aberta) `delete` só age sobre o índice do `model_version` corrente. Índices de outros `model_version`s, se existirem, não são tocados. Hoje o `ai` só tem um `model_version` ativo por modo.
- (issue-95, aberta) A ingestão do `backend` ainda não lê a saída em lote da #68 (`hackathon/.pipeline-output/`, fora do git). O caso 1 usa o Markdown versionado da #59. Falta decidir como o Markdown da #68 chega ao `backend` para o corpus completo: um loader novo sobre o manifesto, ou a ingestão recebendo o caminho do lote. A forma de `index` não muda nas duas opções.
- (issue-95, aberta) O Markdown passa a existir em dois lugares: na saída do pipeline (ou em `hackathon/data/`) e na cópia que o `ai` grava em `extracted_text_locator`. Falta decidir se o localizador deve apontar direto para a saída do pipeline, sem cópia. Isso mudaria quem escreve o localizador. Decisão conservadora do agente: manter o comportamento atual (o `ai` grava a cópia).
- (issue-95, aberta) `original_locator` ([[i4-storage]]) não existe no modelo `DocumentVersion`. O PDF original é achado por `source_pdf_relpath` da fixture (`app/routes/documents.py`). Isso é assunto do catálogo, fora desta fronteira, e fica só registrado aqui.

- (issue-64, aberta) Campo de desempate na ordem total, agora que a unidade é o chunk (antes era `family_id` crescente) — candidatos: `document_version` + posição do chunk, ou um `chunk_id` próprio.
- (issue-28, respondida 2026-09-25 por Eduardo) De que lado fica o agrupamento: **no `backend`**. A decisão da issue-2 foi superada; o `ai` devolve hits crus e o congelamento acontece depois do agrupamento, no `backend`.
- (issue-28) Tempo de retenção do conjunto congelado: enquanto durar a navegação, ou enquanto durar a retenção do `SearchExecution` da issue-9? O segundo é mais simples e já existe. Detalhe de F3.

- (issue-7) Se a ingestão virar contínua (Fog "ingestão contínua a partir de ANEEL/SEI"), "um digest por job" degenera em "um e-mail por documento"; a unidade de agregação passa a ser por período — a chave de dedup e o lugar da política não mudam.
- (issue-7) Especificação concreta do adapter SES (região, identidade remetente, saída do sandbox) — só quando houver conta com SES.

## Evidence

- [Ambiente AWS — serviços disponíveis](../../../../hackathon/docs/Ambiente%20AWS%20-%20serviços%20disponíveis.md), lido em 2026-09-20.
- Eduardo, 2026-09-20: “vamos seguir as sugestões” e “trate esse documento como autoridade para disponibilidade de serviços aws”.

- (issue-7) Plano l.50, 86, 112, 191: F3 é dono da entrega e da deduplicação de e-mails, "prévia local, depois envio controlado; inclui frequência e deduplicação"; aceite = "frequência aplicada e sem duplicação no cenário testado". Plano l.114: a ingestão devolve um id de job. Plano l.134: `PUT /v1/interests` com frequência é evolução.
- (issue-7) `hackathon/scripts/check_aws_capabilities.out` l.317–334: SES negado na conta do hackathon; observação do script sobre sandbox de SES.
- (issue-7) Comentário de resolução da issue #6: eventos base de notificação e o encaminhamento explícito da frequência/dedup para a #7.
- Map issue #1, Notes (decisões de 2026-09-17).
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 60, 102, 118, 128–133, 144, 154–162.

## Topic history

- issue-98 (2026-09-27): expôs `delete(document_version)` em `DELETE /internal/v1/documents/{document_version}`, por decisão do dono do repo. A operação é idempotente, remove chunks do índice e vetores brutos (tombstone) do `model_version` corrente e mantém o texto extraído. A tabela de operações passou a mostrar a rota de `reindex` (#69).

- issue-95 (2026-09-27): alinhou o contrato de `index` à implementação, por decisão do dono do repo. A entrada é o Markdown já extraído inline (`documents[].text`), a extração fica no pipeline #59/#68 antes da fronteira, e o `ai` só grava o texto recebido no localizador. Superou a entrada por localizador do original da issue-15.

- issue-92 (2026-09-27): deu forma concreta a `similar_families` (rota, envelope, agregação por média dos chunks) e a `references[]` (reconhecedor estreito de autos de infração, `locator` = `chunk_id`); ligou os candidatos às arestas de `document_relations` no fim da ingestão.

- issue-64 (em andamento): confirmou que `family_id`/`reassign_family` continuam no contrato do port sem alteração; mudou a unidade de paginação de família para chunk casado, consequência da remoção do agrupamento visual; deixou em aberto só o campo de desempate.

- issue-7 (2026-09-20): revisão de disponibilidade aceita por Eduardo; inventário AWS incorporado como autoridade, corte local preservado. Mantidas as demais decisões desta página.

- issue-7: especificou a entrega de e-mail atrás do port `Mailer` (política de frequência/dedup no backend, antes do port; dedup por `(user_id, document_version_id)`; digest por `(usuário, job)`; `send` idempotente por `email_id`); reformulou "via SES" como independente de adapter.
- issue-15: tirou `get_document` do port e fez `index` trabalhar por localizadores (entrada: original; saída: texto extraído); HTTP restrito a `search`, `index`, `similar_families`, `reassign_family`, `delete`/`reindex`.

- issue-4: acrescentou `references` ao resultado de `index` e a operação `similar_families` ao port; manteve o serviço vetorial como fonte de candidatos, não dono das relações.
- issue-3: refinou a forma do hit por família em `search` (face = versão mais recente; chunks etiquetados por versão) e acrescentou a operação `reassign_family` ao port.
- issue-2: fixou as operações do port (`index`, `search`, `get_document`, `delete`/`reindex`), granularidade por versão/família, agrupamento como obrigação do serviço, o serviço como dono do armazenamento de documentos, e o boundary em duas camadas (port em processo no `ai` + HTTP `/internal/v1/*` para o `backend`).
