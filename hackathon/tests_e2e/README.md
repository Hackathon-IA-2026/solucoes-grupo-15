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
| Feedback (#82) | voto com `request_id` + `document_version` + `chunk_index` de um hit real |
| Stale corpus (#79) | continuação após ingerir um `corpus_version` mais novo devolve `stale_corpus: true` |
| Reindex (#73) | `tools/case1_recall/reindex_from_raw_vectors.py` reconstrói o índice sem AWS e o ranking não muda |

Testes marcados `xfail(strict=True)` documentam divergências ainda abertas entre contrato e comportamento real: relações vindas do `ai` (`similar_families`/`references`), o resultado do processo (#66) e o formato de busca/feedback que o frontend ainda consome. Quando a funcionalidade chegar, o xfail estrito falha e obriga a remover a marcação.
