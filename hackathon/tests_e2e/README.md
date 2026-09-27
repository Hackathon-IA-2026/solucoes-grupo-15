# Suíte e2e: backend ↔ banco vetorial (caso 1)

Issue #88. Sobe backend, `ai`, Postgres e OpenSearch **reais** via Docker Compose, ingere os 10 documentos do caso 1 pelo backend e exercita as rotas públicas `/v1/*` por HTTP, com o `ai` real por trás (sem dublê do `AiClient`).

Roda **inteiramente local e sem credenciais AWS**: o `ai` sobe com `EMBEDDER=cached`, que usa o mesmo pipeline real de `EMBEDDER=bedrock` (chunking 600/800/100 + índice OpenSearch), mas resolve cada vetor Titan V2 em arquivos já computados em vez de chamar o Bedrock:

- vetores brutos da #73 (`.pipeline-output/documents/_raw_vectors/<model_version>.jsonl`), um por chunk;
- vetor da consulta da Carolina do protótipo da #60 (`tools/prototypes/recall_baseline/output/query.json`, versionado).

Texto sem vetor pré-computado vira HTTP 422, nunca um vetor inventado.

## Como rodar

```bash
cd hackathon/tests_e2e
python3.12 -m pip install -r requirements.txt   # uma vez
python3.12 -m pytest -v
```

A suíte sobe o projeto Compose `capiwatt-e2e` (portas 18000/18001/19200, isoladas do `docker compose up` de desenvolvimento), roda os testes e derruba tudo com `down -v`.

Pré-requisitos: Docker, e o arquivo de vetores brutos da #73. Ele fica fora do git (`.pipeline-output/` é ignorado); quem não o tem pode gerá-lo uma vez com `tools/case1_recall/seed_and_measure.py` (exige Bedrock) ou apontar `E2E_RAW_VECTORS_PATH` para uma cópia. Sem ele, a suíte é pulada com uma mensagem explicando o motivo.

| Variável | Efeito |
| --- | --- |
| `E2E_RAW_VECTORS_PATH` | JSONL de vetores brutos da #73 (default acima) |
| `E2E_QUERY_VECTOR_PATH` | JSON `{query, embedding}` da consulta (default: o da #60) |
| `E2E_EMBEDDER=bedrock` | usa o Bedrock real no `ai` (credenciais `AWS_*` repassadas do shell) |
| `E2E_KEEP_STACK=1` | não derruba a stack no fim (depuração) |
| `E2E_EXTERNAL_STACK=1` | não sobe nada; usa `E2E_BACKEND_URL`, `E2E_AI_URL`, `E2E_OPENSEARCH_URL` |

## O que é verificado

| Cenário | Como |
| --- | --- |
| Ingestão real | `POST /v1/ingestions {"corpus": "case1-real", "corpus_version": <hash>}` indexa no OpenSearch os mesmos chunks dos vetores brutos da #73 |
| Catálogo | `corpus_version` do envelope = hash do manifesto da #68 restrito ao caso 1; `localizador` = locator gravado pelo `ai`; texto do documento = Markdown da #59 |
| Idempotência | reingerir não altera a contagem de chunks por `document_version` |
| Busca real | `data_mode="real"`, `model_version` do Titan V2, `Recall@3 >= 2/3` |
| Paginação (#76/#78) | 1ª página chama o `ai` uma vez (log de acesso do container); continuações não chamam; ordem `(-score, document_version, chunk_index)`; `total` exato |
| Replay (#77) | `matches: true` |
| Chunk estável (#96) | cada resultado traz `chunk_id` presente nos vetores brutos da #73 e `chunk_index` = índice real do chunk no documento, igual entre consultas com `top_k` diferentes |
| Feedback (#82) | voto com `request_id` + `document_version` + `chunk_index` de um hit real |
| Busca do frontend (#93) | o envelope real tem exatamente as chaves que `frontend/src/api/search.ts` lê (resultado plano por chunk + `total`/`next_cursor`/`stale_corpus`), e a continuação `{query, cursor}` do "carregar mais" devolve a cauda do mesmo conjunto congelado |
| Feedback do frontend (#94) | o payload de `frontend/src/api/feedback.ts` (chave por chunk, sem `family_id`) é aceito com 200 |
| Stale corpus (#79) | continuação após ingerir um `corpus_version` mais novo devolve `stale_corpus: true` |
| Reindex (#73) | `tools/case1_recall/reindex_from_raw_vectors.py` reconstrói o índice sem AWS e o ranking não muda |
| Relações do `ai` (#92) | `GET /internal/v1/families/{id}/similar` reproduz os vizinhos top-3 e os scores da calibração da #74 (`tools/case1_recall/similarity_calibration/output/calibration_report.json`); o grafo tem exatamente os 11 pares `similar_a` da #74 (`similarity`/`suggested`, com score) e as 7 arestas `referencia` recurso/voto/complementação → auto de infração (`explicit`/`confirmed`, evidência = `chunk_id` existente no índice); reingestão não duplica |

Testes marcados `xfail(strict=True)` documentam divergências ainda abertas entre contrato e comportamento real: hoje só o resultado do processo (#66). Quando a funcionalidade chegar, o xfail estrito falha e obriga a remover a marcação.
