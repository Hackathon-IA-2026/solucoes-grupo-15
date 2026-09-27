---
contract: backend ↔ vector service (`ai`)
sources:
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/i4-storage.md
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/i9-integration.md
  - requirements/perspec-me/capiwatt-lens-hackathon/MAP.md
last_synced_with_sources: 2026-09-27 (issue-64, issue-78, issue-96, issue-92)
---

# Contrato de fronteira: backend ↔ serviço vetorial (`ai`)

Snapshot legível do contrato entre `backend` (F3) e o serviço vetorial (`ai`, F2), extraído das Concern Resolution pages [`i4-storage`](../perspec-me/capiwatt-lens-hackathon/concerns/i4-storage.md) e [`i9-integration`](../perspec-me/capiwatt-lens-hackathon/concerns/i9-integration.md). Este arquivo **não é a fonte de verdade** — é um resumo derivado dela. Em caso de divergência, as Concern Resolution pages prevalecem.

> **Manutenção:** este arquivo deve ser atualizado sempre que `i4-storage.md`, `i9-integration.md` ou o `MAP.md` do caso mudarem de forma a afetar a divisão de posse ou as operações abaixo (nova issue de revisão, novo `supersede`, refresh do `MAP.md`). Ver seção "Como manter em sincronia" no fim.

## Divisão de posse (issue-15)

- **Backend (F3)** é dono do **catálogo documental**: famílias, versões, metadados (checksum, data de coleta, origem, `version_date`), localizador do original e do texto extraído, nó `processo`, sugestões de fusão, `document_relations`, feedback. Grafo e leitura de documento são servidos em processo (`GET /v1/documents/{id}`, `GET /v1/documents/{id}/graph`), sem atravessar a fronteira interna.
- **Serviço vetorial (`ai`, F2)** é dono só do **derivado**: extração de texto, chunking, embeddings, índice vetorial, `references`, `similar_families`. O índice **nunca é fonte de verdade** — é reconstruível a partir do catálogo via `reindex`. `family_id` e `document_version` aparecem no índice só como atributos de filtro.
- Texto extraído: o `ai` extrai durante `index` e escreve num localizador (volume/S3) que o backend só registra no catálogo — não é devolvido inline no `IndexReport`.

## Forma do boundary

Duas camadas: uma interface Python (`VectorService`) em processo dentro do módulo `ai`, com adapters `BedrockEmbedder` e `OpenSearchStore`; o `ai` expõe esse mesmo port por HTTP em `/internal/v1/*`. O `backend` **nunca importa `ai` diretamente** — só chama via cliente HTTP fino, tipado a partir dos mesmos tipos do port. Nenhum tipo do SDK Bedrock/OpenSearch atravessa a fronteira.

## Operações do port

| Operação | Rota `/internal/v1/*` |
|---|---|
| `index(corpus_version, documents[]) → IndexReport` | `/internal/v1/index` |
| `search(query, filters, top_k, as_of?) → SearchResult` | `/internal/v1/search` |
| `delete(document_version)` / `reindex(corpus_version)` | — |
| `reassign_family(document_version, family_id)` | `/internal/v1/documents/{id}/family` |
| `similar_families(family_id, top_k) → [{family_id, score}]` | `GET /internal/v1/families/{id}/similar?top_k=` |

Comportamento:

- **`index`** recebe **localizador do original** (não conteúdo inline); o `ai` extrai o texto (etapa de extração por IA → Markdown verbatim, precisão da issue-13), escreve num localizador (volume/S3) e devolve por versão: `{document_version, extracted_text_locator, references[], chunks_indexed}`. Idempotente por `(document_version, model_version)`.
- **`search`** devolve **hits crus por chunk** (agrupamento por família saiu do serviço na issue-28, e a issue-64 removeu o agrupamento por família também da visualização; a issue-78 removeu o agrupamento visual por família na resposta do backend): cada hit com `family_id`, `document_version`, `chunk_id`, `chunk_index`, `excerpt`, localizador, score — `family_id` continua no envelope como atributo de filtro/dado, mas o `backend` não agrupa mais por ele. Envelope carrega `corpus_version` e `model_version`. Congelamento da lista ordenada e paginação (`cursor`/`limit`/`next_cursor`/`total`) são responsabilidade do **backend**; a unidade de paginação é o **chunk casado** (issue-64), não mais a família. **Ordenação determinística** (issue-78): o backend ordena os chunks por `(-score, document_version, chunk_index)` — score decrescente, desempate lexicográfico por `document_version`, desempate final pelo `chunk_index` real do chunk (issue-96).
- **Identidade do chunk** (issue-96): `chunk_id` é o id do chunk no índice (`"<document_version>#chunk-NNNN"`, formato do `ai`) e `chunk_index` é o índice real do chunk dentro do documento (0-based), já resolvido pelo `ai` — o `backend` nunca faz parsing do `chunk_id` e nunca usa a posição do hit na lista. O `backend` repassa os dois em cada resultado de `POST /v1/search`; `(document_version, chunk_index)` é a chave de chunk do feedback (#82) e dos `evidence_refs` (#66), estável entre consultas e entre reindexações do mesmo `model_version`.
- **`similar_families`** e `references` (dentro do `IndexReport`) entregam só **candidatos** de arestas do grafo — resolução de id, limiares, gravação e curadoria de `document_relations` são do backend (issue-92):
  - `GET /internal/v1/families/{family_id}/similar?top_k=3` (padrão 3) → `{family_id, model_version, similar: [{family_id, score}]}`. Vetor de família = média renormalizada dos embeddings de todos os chunks da família no índice (agregação calibrada na #74); score = produto interno; a própria família nunca aparece; família sem chunks no índice → 404. O `ai` não aplica limiar. Modo fixture: `similar: []`.
  - `IndexReport.references: [{identifier_raw, relation_type, locator}]` — `identifier_raw` é o trecho citado (espaços normalizados), `relation_type` é `null` enquanto os tipos finos não tiverem padrão, `locator` é o `chunk_id` do chunk onde a citação foi achada. Hoje só "Auto de Infração [– AI –] nº N/AAAA[-SIGLA]" é reconhecido. Modo fixture: lista vazia.
  - O backend, no fim da ingestão, grava `similar_a` (`origin: similarity`, `status: suggested`, `score`) quando `0.80 <= score < 0.97` (`limiar_relacao`/`limiar_fusao` da #74), uma vez por par, e `referencia` (`origin: explicit`, `status: confirmed`, evidência `document_version` + `chunk_id`) quando o identificador resolve para uma única família do catálogo diferente da fonte.
- **`delete` / `reindex`** existem porque troca de modelo de embeddings exige reindexar; vetores de modelos diferentes nunca se misturam.
- **`reassign_family`** move uma versão (e seus chunks/vetores) para outra família sem reembedding.

## Operação removida do port

- **`get_document`** — removida pela issue-15. O backend lê documentos do próprio catálogo; não existe mais proxy `/internal/v1/documents/{id}`.

## Teste de contrato

Os testes de contrato do port rodam contra o adapter Bedrock **e** contra um adapter fake/local; os mesmos testes rodam contra o fake em processo e contra a superfície HTTP real do `ai`. Isso garante que trocar Bedrock/OpenSearch por outro backend (ex.: pgvector) não muda o contrato visto pelo `backend`.

## Como manter em sincronia

1. Toda mudança que altere este contrato nasce como revisão de issue nas Concern Resolution pages `i4-storage` e/ou `i9-integration` (fluxo `perspec-me`), nunca direto aqui.
2. Depois que a Concern Resolution page for atualizada (novo `supersede`, nova operação, mudança de posse), atualize este arquivo para refletir o estado **vigente** (não histórico) — só a seção "Current resolution" de cada Concern importa, não o texto tachado.
3. Atualize `last_synced_with_sources` no frontmatter para a data do refresh.
4. Se o `MAP.md` do caso for refreshado e isso tocar I4 ou I9, revise este arquivo na mesma sessão.
