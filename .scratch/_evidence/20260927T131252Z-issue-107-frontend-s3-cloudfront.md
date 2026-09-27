# Evidence Pack

- **ID do pack:** EVP-107-60c36f0
- **Versão do template:** 1.0
- **Gerado em (UTC):** 2026-09-27T13:13Z
- **Status geral:** `PARTIAL`
- **Modo da tarefa:** github (publicação **pendente de autorização do dono**; pack gravado só localmente)
- **Referência da tarefa:** Hackathon-IA-2026/solucoes-grupo-15#107, parent #101
- **Repositório:** Hackathon-IA-2026/solucoes-grupo-15
- **Branch:** `docs/perspec-me-issues-99-100` (local, sem push)
- **Revisão base:** `bd919ed`
- **Revisão atual:** `60c36f0`
- **Estado da árvore de trabalho:** suja, mas não por este trabalho. `hackathon/` está limpo em `60c36f0`. As mudanças não commitadas em `requirements/perspec-me/capiwatt-aws-deploy/` (6 arquivos modificados e `m5-performance-metrics.md` novo) já existiam antes da sessão e não foram tocadas. Este pack fica em `.scratch/_evidence/`, que não é versionado.
- **Produtor:** agente Claude Code (Claude Opus 5.5), sessão da issue #107

## 1. Resultado executivo

O comportamento padrão da distribuição CloudFront agora serve o frontend a partir de um bucket S3 privado, via OAC. Uma CloudFront Function faz o fallback de SPA, sem error responses globais. O `cdk deploy` roda o build do Vite e publica o resultado em dois `BucketDeployment`: JS/CSS com hash com cache longo, e o resto, junto com o `config.json` gerado pelo CDK sem Cognito, em `no-cache` e com invalidação. Tudo isso está no commit `60c36f0`, que foi implantado de verdade em us-west-2.

Verificamos pela URL do CloudFront:

- os cabeçalhos de cache;
- o fallback de SPA e os deep links, inclusive o de processo com ponto e `%2F`;
- o 404 JSON da API;
- o OAC (o acesso direto ao S3 dá 403);
- a invalidação: uma mudança no frontend apareceu 19 s depois do fim do update do stack, substituindo um objeto que estava em "Hit" na borda.

Os 22 testes de synth passam.

**Status PARTIAL, só por causa do critério 1.** O app abre em modo demo, e documento, grafo e notificações funcionam pela mesma origem, sem CORS. Duas telas, porém, falham por incompatibilidades de contrato frontend↔backend que **já existiam** e não dependem da hospedagem:

- a busca na tela chama `/v1/search` (200), mas não renderiza os resultados. O frontend lê `result.face`/`matched_chunks`, e o backend devolve resultados planos por chunk desde a #78 (`75dd350`);
- o botão de feedback envia um payload sem `document_version`/`chunk_index`, que são obrigatórios desde a #82, e recebe 422. Com o payload do contrato atual, `/v1/feedback` responde 200 pela mesma origem.

**O ambiente continua de pé na AWS**, em `AUTH_MODE=none`, por instrução do dono: `cdk destroy` só depois de consultá-lo.

## 2. Mapa escopo → prova

| ID | Requisito ou propriedade | Fonte | Verificação | Evidências | Status |
| --- | --- | --- | --- | --- | --- |
| CLM-001 | A URL do CloudFront abre o app em modo demo | AC 1 | Playwright: `/` leva à tela "Entrar", login demo → persona → `/explorar`; `/config.json` = `{"region":"us-west-2"}` com 200 | EVD-005, EVD-003 | `PASS` |
| CLM-002 | As chamadas da API saem da mesma origem, sem CORS | AC 1 | Playwright: 48 chamadas `/v1/*` no mesmo host e nenhuma requisição falhou (fora os `ERR_ABORTED` de navegação). A única origem externa é o Google Fonts do próprio `index.html` | EVD-005 | `PASS` |
| CLM-003 | O documento funciona | AC 1 | `GET /v1/documents/fam-norma-1000` 200, e a tela mostra "Versões registradas" | EVD-005 | `PASS` |
| CLM-004 | O grafo funciona | AC 1 | `GET /v1/documents/{id}/graph` 200, e o painel de relações é renderizado (documento e processo) | EVD-005 | `PASS` |
| CLM-005 | As notificações funcionam | AC 1 | Na tela `/notificacoes`: escolha do escopo, `PUT notification-scope` 200 e `GET /v1/users/carolina/notifications` 200 com 15 itens. `/integracoes/notificacoes` responde 200 | EVD-005 | `PASS` |
| CLM-006 | A busca funciona | AC 1 | O `POST /v1/search` pela tela `/explorar` dá 200 com 10 resultados (`data_mode=real`), mas a tela mostra "Não foi possível carregar os dados." | EVD-005, EVD-010 | `FAIL` (contrato preexistente, #78; não é da hospedagem) |
| CLM-007 | O feedback funciona | AC 1 | Um `fetch` da página com o payload do contrato atual dá 200. Com o payload que o frontend envia hoje, dá 422 (`document_version` ausente) | EVD-005, EVD-010 | `FAIL` (contrato preexistente, #82; o transporte pela mesma origem funciona) |
| CLM-008 | Deep links carregam o app na rota certa | AC 2 | `curl` com 200 e `<div id="root">` em `/explorar`, `/documents/...`, `/processos/48500.001234%2F2024-11` e `/integracoes/notificacoes`. No Playwright, uma carga completa de `/documents/fam-norma-1000` e de `/processos/48500.901433%2F2024-53` renderiza as telas certas | EVD-003, EVD-005 | `PASS` |
| CLM-009 | `/v1/documents/<inexistente>` devolve 404 JSON, e não o `index.html` | AC 3 | `HTTP/2 404`, `content-type: application/json`, `{"detail":"Familia nao encontrada"}`. `/v1/nao-existe-107` também dá 404 JSON | EVD-003 | `PASS` |
| CLM-010 | `index.html` e `config.json` com `no-cache`, e assets com hash com cache longo | AC 4 | `cache-control: no-cache` em `/`, `/index.html`, `/config.json` e nos deep links. `public, max-age=31536000, immutable` em `assets/index-*.js` e `.css`. Imagens de `public/` sem hash saem com `no-cache` | EVD-003 | `PASS` |
| CLM-011 | Os testes de synth cobrem OAC, a associação da Function ao comportamento padrão e a ausência de error responses globais | AC 5 | `test_default_behavior_serves_the_frontend_from_a_private_bucket_through_oac` e `test_spa_fallback_is_a_viewer_request_function_on_the_default_behavior_only`. Na mutação, uma `error_responses` 403 → `/index.html` fez o teste falhar | EVD-001, EVD-002 | `PASS` |
| CLM-012 | Um novo `cdk deploy` com mudança no frontend aparece sem esperar o cache | AC 6 | Com a borda em "Hit" no `index.html` antigo, foi feito um deploy só do `CapiwattCompute` com o título "(sonda 107)" e um `console.info`. 19 s depois do `UPDATE_COMPLETE`, `/`, `/index.html` e `/explorar` já serviam o título novo e o JS `index-eyXIk9TG.js` com a sonda. A sonda foi revertida sem commit e reimplantada | EVD-006, EVD-007 | `PASS` |
| CLM-013 | Bucket privado, lido só pela distribuição (OAC) | Escopo da issue | Acesso direto `https://<bucket>.s3.us-west-2.amazonaws.com/index.html` → 403. Block Public Access com as 4 opções `true`. A policy só dá `s3:GetObject` ao principal `cloudfront.amazonaws.com` com `AWS:SourceArn` da distribuição. Arquivo ausente atrás do CloudFront → 403 do S3, sem virar `index.html` | EVD-004, EVD-003 | `PASS` |
| CLM-014 | O fallback de SPA preserva os arquivos estáticos e trata ids com ponto como rota | Escopo da issue (Function) | `tests/test_spa_rewrite.py` executa a Function no node. Os assets reais servidos pelo CloudFront voltam 200 com o content-type certo | EVD-001, EVD-003 | `PASS` |
| CLM-015 | Sem sobras no destroy: bucket esvaziado e Lambdas de custom resource logando num log group do stack com retenção | Regra geral da #106 (tudo DESTROY, sem sobras) | Testes `test_destroy_empties_the_frontend_bucket` e `test_every_lambda_logs_to_a_log_group_of_the_stack_with_retention`. Na conta: `/capiwatt/frontend-deploy` com retenção de 3 dias e 3 streams, e **nenhum** `/aws/lambda/Capiwatt*` | EVD-001, EVD-008 | `PARTIAL` (o `cdk destroy` não rodou: o dono pediu para ser consultado antes) |

## 3. Inventário de mudanças

- **Adicionados:**
  - `hackathon/infra/capiwatt_infra/frontend.py`: `FrontendSite`, bucket, OAC, Function, build local via `ILocalBundling` com fallback Docker `node:22-alpine`, dois `BucketDeployment` e `runtime_config`;
  - `hackathon/infra/capiwatt_infra/spa_rewrite.js`;
  - `hackathon/infra/tests/test_spa_rewrite.py`.
- **Modificados:**
  - `hackathon/infra/capiwatt_infra/compute_stack.py`: o comportamento padrão passa a ser o `FrontendSite`, e `publish(distribution)` roda depois da distribuição;
  - `hackathon/infra/tests/test_app.py`: 7 testes novos; os apps de teste ficam sem bundling (`aws:cdk:bundling-stacks: []`), e a lista de log groups passa a incluir `/capiwatt/frontend-deploy`.
- **Removidos:** nenhum.
- **Config/schema:** nenhum contexto CDK novo. O `config.json` publicado é `{"region": "us-west-2"}`.
- **Comportamento visível:**
  - `https://<cloudfront>/` serve o app, e a API continua em `/v1/*`;
  - novo log group `/capiwatt/frontend-deploy`, com retenção de 3 dias;
  - o `cdk deploy` passa a exigir `npm` ou Docker na máquina do time.
- **Não tocados de propósito:**
  - Cognito (#108), `seed.sh` e o README do infra (#109);
  - código do frontend e do backend. As duas incompatibilidades de contrato (CLM-006/007) ficaram fora do escopo;
  - `requirements/contracts/` (a fronteira frontend↔backend não mudou) e os arquivos perspec-me com mudanças locais do dono.

## 4. Pacote de verificação

- **Testes executados:** a suíte do infra (22) em `60c36f0`.
- **Testes novos:** 7 em `test_app.py` e 2 em `test_spa_rewrite.py`. Cada fatia foi vermelha antes e verde depois: OAC; Function; lógica da Function; publicação, cache e config (3 testes); sem sobras (2 testes).
- **Casos de borda:**
  - id de processo com ponto, com e sem `%2F`;
  - `/documents/` com barra final;
  - asset `.js` inexistente (continua arquivo e não vira `index.html`);
  - imagens de `public/assets` sem hash (ficam em `no-cache`);
  - assets antigos preservados (`prune=False`). O JS anterior continuou 200 depois do deploy da sonda.
- **Integração/e2e (AWS real, us-west-2):**
  - deploy completo;
  - curl de cabeçalhos, status e deep links;
  - OAC e policy;
  - ingestão demo via ECS Exec;
  - Playwright headless (Chromium) com 9 telas;
  - deploy da sonda e da reversão;
  - log groups.
- **Não executados:** `cdk destroy` e a varredura de sobras (o dono quer ser consultado antes). A suíte do frontend e a do backend não rodaram: nenhum dos dois foi alterado.

| Comando | Exit | Resultado | Evidência |
| --- | --- | --- | --- |
| `pytest -q` (em `hackathon/infra`, venv py3.12, aws-cdk-lib 2.271.0) | 0 | `22 passed` | EVD-001 |
| mutação: `error_responses=[403 → /index.html]` na distribuição + `pytest -q -k spa_fallback`, depois revertida | 1 → 0 | falhou com a mutação e passou depois de revertida | EVD-002 |
| `npx -y aws-cdk@2.1143.0 synth --quiet -c opensearch_service_linked_role=existing` | 0 | build do Vite no asset (`index-x2ywK11e.js`), 3 stacks; `config.json` = `{"region":"us-west-2"}` | EVD-001 |
| `npx -y aws-cdk@2.1143.0 deploy --all --require-approval never -c opensearch_service_linked_role=existing` (12:36Z) | — (a sessão do agente foi morta durante o deploy) | O deploy terminou sozinho: `CapiwattNetwork`, `CapiwattData` e `CapiwattCompute` em `CREATE_COMPLETE` (Compute 12:52–12:59Z), conferido com `aws cloudformation describe-stacks` | EVD-009 |
| `curl_checks.sh <cloudfront>` + códigos de status | 0 | ver CLM-008/009/010/013 | EVD-003 |
| `aws s3api get-public-access-block` / `get-bucket-policy` / `curl` direto no S3 | 0 | 4 × `true`; `GetObject` só para o CloudFront com `SourceArn`; acesso direto 403 | EVD-004 |
| ECS Exec → `POST localhost:8000/v1/ingestions` | 0 | `200 {"families_count":14,"versions_count":15,"relations_count":16}` em 8,9 s | EVD-011 |
| `node e2e.mjs <cloudfront>` (Playwright 1.61.1, execução 5) | 1 | 16 OK, 3 FAIL: busca renderizada (CLM-006), payload de feedback do frontend (CLM-007) e o erro de console 422 gerado por esse mesmo envio de propósito | EVD-005 |
| `cdk deploy CapiwattCompute --exclusively ...` com a sonda | 0 | só os 2 `Custom::CDKBucketDeployment` foram atualizados (Shell `UPDATE_COMPLETE` 13:09:57Z); 53 s | EVD-006 |
| `curl` antes (13:08:12Z) e depois (13:10:16Z) | 0 | antes: etag `6570e73a…`, "Hit/RefreshHit", título antigo. Depois: etag `0e139495…`, título "(sonda 107)", `index-eyXIk9TG.js` com `sonda-107` e `immutable`, JS antigo ainda 200 | EVD-007 |
| reversão da sonda + `cdk deploy CapiwattCompute --exclusively ...` | 0 | título original e `index-x2ywK11e.js` de volta (o build é reprodutível); `git status hackathon/` limpo | EVD-006 |
| `aws logs describe-log-groups` (`/capiwatt`, `/aws/lambda/Capiwatt`) | 0 | `/capiwatt/{ai,backend,frontend-deploy}` com retenção de 3 dias; nenhum `/aws/lambda/Capiwatt*` | EVD-008 |
| `ruff check .` / `ruff format --check .` (em `hackathon/infra`) | 0 | "All checks passed!", "9 files already formatted" | EVD-001 |

## 5. Higiene de engenharia

| Categoria | Status | Evidência |
| --- | --- | --- |
| Linting | `PASS`: `ruff check` no infra | EVD-001 |
| Formatação | `PASS`: `ruff format --check` | EVD-001 |
| Análise estática | `NOT_RUN` (`cfn-lint` não foi executado) | — |
| Checagem de tipos | `NOT_RUN` | — |
| Build | `PASS`: `cdk synth` com o build do Vite no asset e 3 deploys reais | EVD-001, EVD-006, EVD-009 |
| Regras do repo | `PASS`: segue a ADR-0002 e a topic-frontend-hosting (S3 privado + OAC, Function sem error responses, `config.json` em runtime, `no-cache`/cache longo); tudo em DESTROY; nenhum ID de conta literal (teste); docstrings em português sem acento, como no código vizinho | EVD-001 |

## 6. Plano × execução

- **Plano conceitual:** fatias TDD (OAC → Function → lógica da Function → publicação/cache/config → sem sobras), commit, deploy real, verificação dos 6 critérios pela URL do CloudFront, sonda de invalidação, `destroy` e pack publicado na issue.
- **Execução:** as fatias TDD, o commit `60c36f0`, o deploy e a verificação completa. A sonda foi implantada, revertida e reimplantada.
- **Desvios:**
  - **Sessão morta durante o `cdk deploy --all`** (terminal fechado, exit 137). O deploy terminou sozinho na AWS e não foi refeito. O log `deploy1.log` ficou truncado no meio do `CapiwattCompute`, e o estado final foi conferido com `describe-stacks`.
  - **Mudança de instrução do dono no meio da sessão:** não rodar `cdk destroy`, não comentar na issue e não fazer push sem consultá-lo antes. Por isso o pack ficou só local, o ambiente continua de pé e CLM-015 ficou `PARTIAL`.
  - **Frontend e backend sem correção:** as falhas de busca e feedback (CLM-006/007) são incompatibilidades de contrato anteriores à #107 e fora do escopo dela. O dono decide o ticket.
  - **Reimplantação da reversão da sonda:** um deploy a mais (53 s, só custom resources), para que o ambiente de pé sirva exatamente o `60c36f0`.
  - **Teste de log groups da #106 ampliado** com `/capiwatt/frontend-deploy`, o log group novo.

## 7. Racional e trade-offs

- **Dois `BucketDeployment`:** o `cache_control` vale para todos os objetos de um deployment, então os JS/CSS com hash (`assets/*.js|css`) ficam num deployment e o resto em outro. As imagens de `public/assets` não têm hash e por isso ficam em `no-cache`. O shell depende dos assets, para que o `index.html` novo nunca aponte para um JS ainda não publicado. Os assets antigos ficam no bucket (`prune=False`), porque uma aba aberta com o `index.html` anterior ainda pede esses arquivos.
- **Fallback por extensão, e não por "tem ponto":** a Function trata como arquivo só um último segmento terminado em `.` + letra + até 9 alfanuméricos. Ids SEI como `48500.001234%2F2024-11` continuam sendo rotas.
- **`auto_delete_objects` com `LoggingConfig` por override:** o handler do `BucketDeployment` pula o `rm` no delete quando o bucket tem a tag `aws-cdk:cr-owned`, e essa tag sempre existe num bucket do mesmo stack. Por isso o esvaziamento no destroy precisa do `auto_delete_objects`. A Lambda dele não aceita log group, e sem `LoggingConfig` criaria `/aws/lambda/*` sem retenção, que sobraria depois do destroy. Por isso recebe o `LoggingConfig` por escape hatch, como a Lambda do `BucketDeployment` já recebe via `log_group`.
- **Build local, com Docker como fallback:** usa o `npm` da máquina do time, que é mais rápido e não exige a imagem `node`. Os testes pulam o bundling.
- **Alternativas descartadas:**
  - error responses 403/404 → `index.html`: mascaram os 404 da API;
  - stack de frontend separado: gera um ciclo entre a policy do bucket (ARN da distribuição) e a origem da distribuição (bucket);
  - custom resource próprio para esvaziar o bucket: mais código, com o mesmo problema de log.

## 8. Arquivo de exploração

- As execuções 1 a 4 do Playwright falharam por causa do próprio script: a espera pela tela de busca era por texto, o `/notificacoes` pede o escopo antes, e o botão se chama "Ativar notificações". O script foi ajustado até a execução 5. Os logs estão em `scratchpad/e2e{1..5}.log`.
- O primeiro wrapper do deploy da sonda usou `setsid`, que devolveu `exit=0` antes do fim do deploy. A conclusão foi esperada pelo `✅ CapiwattCompute` no log.

## 9. Riscos, rollback e limitações

- **Risco residual:**
  - **o ambiente está de pé, com `AUTH_MODE=none` e a URL pública.** Ele inclui `/v1/ingestions` e `/v1/demo/reset` abertos. Destruir assim que o dono autorizar (`cdk destroy --all --force -c opensearch_service_linked_role=existing` em `hackathon/infra`) e fazer a varredura de sobras da #106 mais o bucket do frontend;
  - o `cdk deploy` passa a depender de `npm` ou Docker;
  - o caminho de fallback Docker do bundling nunca foi exercitado.
- **Rollback:** `git revert 60c36f0`. Nesse caso, o comportamento padrão volta ao ALB provisório.
- **Trabalho incompleto:** `cdk destroy` e a prova de "sem sobras" (CLM-015), à espera do dono.
- **Premissas:** a sessão anterior foi encerrada durante o deploy 1. A saída dele está em `deploy1.log` (316 linhas, truncado), e o estado dos stacks foi conferido às 13:00Z.
- **Limitações de ambiente:** o `WSParticipantRole` não lê CloudFront diretamente. A Function e os cabeçalhos foram verificados pelo comportamento HTTP.
- **Evidência ausente:**
  - log completo do deploy 1;
  - destroy e varredura;
  - `cfn-lint`.
- **Follow-up, a decidir pelo dono:**
  - issue para alinhar o frontend ao envelope plano da busca da #78 (`api/search.ts`, `SearchPage`, `ApiAppRepository.mapSearchEnvelope`);
  - issue para o `submitFeedback` enviar `document_version`/`chunk_index` (#82);
  - publicar este pack na #107.

## 10. Cadeia de custódia

Artefatos no scratchpad local do agente (`/tmp/claude-1000/.../scratchpad/`), não versionados. Todos foram produzidos pelo agente em `docs/perspec-me-issues-99-100` @ `60c36f0`. Os logs com saída de AWS tiveram o ID de conta substituído por `<conta>` na captura, exceto o `deploy*.log` bruto, que não está neste pack. A URL do CloudFront e o nome do bucket estão omitidos aqui (`<cloudfront>`, `<bucket>`) porque o ambiente continua aberto.

| ID | UTC | Comando/ferramenta | Ponteiro | SHA-256 |
| --- | --- | --- | --- | --- |
| EVD-001 | 2026-09-27T13:12Z | pytest 8.3.3, ruff 0.6.9, aws-cdk 2.1143.0 / aws-cdk-lib 2.271.0, Python 3.12 | `final-tests.log` | `63021a81b5d73c2f823610ab64436d7d603374245bee1d9e4956439b999c191a` |
| EVD-002 | 2026-09-27 ~12:30Z | mutação + pytest | `mutation-error-responses.log` | `56683de51d6d0a2d9c282a666c96bd118979a7dae4c9970c051737699d30420f` |
| EVD-003 | 2026-09-27T13:01:04Z | curl | `curl1.log`, `curl1-status.log`, `curl_checks.sh` | `c6549e7c343cfdbc0dbd21a644d70bc9b9d15103efb67b253258bfe60c8b98a7`, `e73bc80bde46876d425f3f4229bb142527f6f90c4e1fda88b7b1548c82a78f71`, `69d719fe237c8b5a5c3b8dbc1c53c8a3dacbeeae161157c01f8a75c3a240b0b1` |
| EVD-004 | 2026-09-27 ~13:01Z | aws-cli v2 (s3api), curl | saída de terminal da sessão | — |
| EVD-005 | 2026-09-27T13:07:33Z | Playwright 1.61.1 / Chromium headless, node 22.2.0 | `e2e5.log`, `pw/e2e.mjs`, `shots5/*.png` | `0ffa1e13e6b59da83501701e5619eb1870940e0b403446ed5bcb20f13f176efb`, `124e283667fb9417d7d5e9527e38388dea067674c116651080dd26d659fc3d5c` |
| EVD-005 (telas) | idem | idem | `shots5/03-busca.png`, `05-documento-grafo.png`, `07-deeplink-processo.png`, `08-notificacoes.png` | `ff60ca3c…18c6`, `54158d2b…fdcb`, `523033fc…4e24`, `24768c36…3c4c` |
| EVD-006 | 2026-09-27T13:08:23Z–13:12Z | `cdk deploy CapiwattCompute --exclusively` (sonda e reversão) | `deploy2.log`, `deploy3.log` | `e0f34c2eb1a960e3ddba9c53e5c63e528186b5c9dbf94912c648b4a11018b200`, `96f4ec1892094f29fe9da4a3aa247de32f364be0007fb9d88c0243d9d71977f4` |
| EVD-007 | 2026-09-27T13:08:12Z / 13:10:16Z | curl | `redeploy-before.log`, `redeploy-after.log` | `4303c03ddcc7538de58ea7238e472759db0055199de4301491162eabff9b1004`, `d93a719c7c22a7b1d9ac3548cc48b46edae5bc64dc804c340935c546d561782a` |
| EVD-008 | 2026-09-27 ~13:12Z | aws logs | `loggroups.log` | `a67754ee77b76584354a6af06f4f1acfab13d7656a2f6e34188fcfce8be9c494` |
| EVD-009 | 2026-09-27T12:36:51Z → 13:00Z | `cdk deploy --all` + `describe-stacks` | `deploy1.log` (truncado) | `0a9671c74f4d578b32858085b92379cbb8c8f43fb703aab30855a3d78980b2fe` |
| EVD-010 | 2026-09-27 | leitura de código e histórico | `git log 75dd350` (#78); `backend/app/routes/feedback.py` `FeedbackIn` (#82); `frontend/src/api/feedback.ts`, `services/appRepository.ts` | — |
| EVD-011 | 2026-09-27T13:02:02Z | aws ecs execute-command | `ingest.log` | `30b8f2e2d81c094cdabc5922443639b88ae21f088f9bf084a521263aff78f312` |

## 11. Manifesto legível por máquina

<!-- evidence-manifest:start -->

```yaml
manifest_version: "1.0"
pack_id: "EVP-107-60c36f0"
task:
  mode: "github"
  reference: "Hackathon-IA-2026/solucoes-grupo-15#107"
repository:
  branch: "docs/perspec-me-issues-99-100"
  base_revision: "bd919ed"
  current_revision: "60c36f0"
generated:
  at_utc: "2026-09-27T13:13:00Z"
  producer: "agente Claude Code (Claude Opus 5.5)"
publication: "pendente de autorizacao do dono (pack apenas local)"
claims:
  - {id: "CLM-001", status: "PASS", evidence_ids: ["EVD-005", "EVD-003"]}
  - {id: "CLM-002", status: "PASS", evidence_ids: ["EVD-005"]}
  - {id: "CLM-003", status: "PASS", evidence_ids: ["EVD-005"]}
  - {id: "CLM-004", status: "PASS", evidence_ids: ["EVD-005"]}
  - {id: "CLM-005", status: "PASS", evidence_ids: ["EVD-005"]}
  - {id: "CLM-006", status: "FAIL", evidence_ids: ["EVD-005", "EVD-010"]}
  - {id: "CLM-007", status: "FAIL", evidence_ids: ["EVD-005", "EVD-010"]}
  - {id: "CLM-008", status: "PASS", evidence_ids: ["EVD-003", "EVD-005"]}
  - {id: "CLM-009", status: "PASS", evidence_ids: ["EVD-003"]}
  - {id: "CLM-010", status: "PASS", evidence_ids: ["EVD-003"]}
  - {id: "CLM-011", status: "PASS", evidence_ids: ["EVD-001", "EVD-002"]}
  - {id: "CLM-012", status: "PASS", evidence_ids: ["EVD-006", "EVD-007"]}
  - {id: "CLM-013", status: "PASS", evidence_ids: ["EVD-004", "EVD-003"]}
  - {id: "CLM-014", status: "PASS", evidence_ids: ["EVD-001", "EVD-003"]}
  - {id: "CLM-015", status: "PARTIAL", evidence_ids: ["EVD-001", "EVD-008"]}
artifacts:
  - {id: "EVD-001", category: "test", status: "PASS", claim_ids: ["CLM-011", "CLM-014", "CLM-015"], command: "pytest -q && ruff check . && ruff format --check . && cdk synth --quiet", working_directory: "hackathon/infra", exit_code: 0, pointer: "scratchpad/final-tests.log", sha256: "63021a81b5d73c2f823610ab64436d7d603374245bee1d9e4956439b999c191a", tool: "pytest", tool_version: "8.3.3"}
  - {id: "EVD-002", category: "test", status: "PASS", claim_ids: ["CLM-011"], command: "mutacao error_responses + pytest -q -k spa_fallback", working_directory: "hackathon/infra", exit_code: 1, pointer: "scratchpad/mutation-error-responses.log", sha256: "56683de51d6d0a2d9c282a666c96bd118979a7dae4c9970c051737699d30420f"}
  - {id: "EVD-003", category: "log", status: "PASS", claim_ids: ["CLM-001", "CLM-008", "CLM-009", "CLM-010", "CLM-013", "CLM-014"], command: "curl_checks.sh <cloudfront>", working_directory: "scratchpad", exit_code: 0, pointer: "scratchpad/curl1.log", sha256: "c6549e7c343cfdbc0dbd21a644d70bc9b9d15103efb67b253258bfe60c8b98a7", generated_at_utc: "2026-09-27T13:01:04Z"}
  - {id: "EVD-004", category: "log", status: "PASS", claim_ids: ["CLM-013"], command: "aws s3api get-public-access-block / get-bucket-policy; curl direto no S3", working_directory: ".", exit_code: 0, pointer: "terminal da sessao"}
  - {id: "EVD-005", category: "other", status: "PARTIAL", claim_ids: ["CLM-001", "CLM-002", "CLM-003", "CLM-004", "CLM-005", "CLM-006", "CLM-007", "CLM-008"], command: "node e2e.mjs <cloudfront> shots5", working_directory: "scratchpad/pw", exit_code: 1, pointer: "scratchpad/e2e5.log", sha256: "0ffa1e13e6b59da83501701e5619eb1870940e0b403446ed5bcb20f13f176efb", tool: "playwright", tool_version: "1.61.1", generated_at_utc: "2026-09-27T13:07:33Z"}
  - {id: "EVD-006", category: "build", status: "PASS", claim_ids: ["CLM-012"], command: "npx -y aws-cdk@2.1143.0 deploy CapiwattCompute --exclusively --require-approval never -c opensearch_service_linked_role=existing", working_directory: "hackathon/infra", exit_code: 0, pointer: "scratchpad/deploy2.log, deploy3.log", sha256: "e0f34c2eb1a960e3ddba9c53e5c63e528186b5c9dbf94912c648b4a11018b200"}
  - {id: "EVD-007", category: "log", status: "PASS", claim_ids: ["CLM-012"], command: "curl antes/depois do deploy da sonda", working_directory: "scratchpad", exit_code: 0, pointer: "scratchpad/redeploy-after.log", sha256: "d93a719c7c22a7b1d9ac3548cc48b46edae5bc64dc804c340935c546d561782a", generated_at_utc: "2026-09-27T13:10:16Z"}
  - {id: "EVD-008", category: "log", status: "PASS", claim_ids: ["CLM-015"], command: "aws logs describe-log-groups --log-group-name-prefix /capiwatt | /aws/lambda/Capiwatt", working_directory: ".", exit_code: 0, pointer: "scratchpad/loggroups.log", sha256: "a67754ee77b76584354a6af06f4f1acfab13d7656a2f6e34188fcfce8be9c494"}
  - {id: "EVD-009", category: "log", status: "PARTIAL", claim_ids: [], command: "npx -y aws-cdk@2.1143.0 deploy --all --require-approval never -c opensearch_service_linked_role=existing; aws cloudformation describe-stacks", working_directory: "hackathon/infra", exit_code: -1, pointer: "scratchpad/deploy1.log (truncado; sessao morta, stacks CREATE_COMPLETE)", sha256: "0a9671c74f4d578b32858085b92379cbb8c8f43fb703aab30855a3d78980b2fe"}
  - {id: "EVD-010", category: "diff", status: "FAIL", claim_ids: ["CLM-006", "CLM-007"], command: "git log 75dd350; leitura de FeedbackIn e api/feedback.ts", working_directory: ".", exit_code: 0, pointer: "contrato preexistente frontend x backend (#78, #82)"}
  - {id: "EVD-011", category: "log", status: "PASS", claim_ids: ["CLM-003", "CLM-004", "CLM-005"], command: "aws ecs execute-command ... POST http://localhost:8000/v1/ingestions", working_directory: ".", exit_code: 0, pointer: "scratchpad/ingest.log", sha256: "30b8f2e2d81c094cdabc5922443639b88ae21f088f9bf084a521263aff78f312"}
```

<!-- evidence-manifest:end -->

<!-- evidence-pack:#107:60c36f0 -->
