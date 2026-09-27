---
contract: frontend ↔ backend
sources:
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/u3-frequency.md
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/u4-visualization.md
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/i6-telemetry.md
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/i9-integration.md
  - requirements/perspec-me/capiwatt-lens-hackathon/concerns/u6-acceptance.md
  - hackathon/tests_e2e/test_case1_e2e.py
  - requirements/perspec-me/capiwatt-lens-hackathon/MAP.md
  - requirements/perspec-me/capiwatt-aws-deploy/concerns/i9-integration.md
  - requirements/perspec-me/capiwatt-aws-deploy/concerns/u6-acceptance.md
  - hackathon/docs/adr/0001-stack-scaffold-local.md
last_synced_with_sources: 2026-09-27
---

# Contrato de fronteira: frontend ↔ backend

Snapshot legível do contrato entre a aplicação de interface (`frontend`, F1) e a API do catálogo e serviços de aplicação (`backend`, F3). Este arquivo foi derivado dos módulos de comunicação em [`hackathon/frontend/src/api/`](../../hackathon/frontend/src/api/), das rotas FastAPI em [`hackathon/backend/app/routes/`](../../hackathon/backend/app/routes/) e das Concern Resolution pages de experiência do usuário e integração ([`u3-frequency`](../perspec-me/capiwatt-lens-hackathon/concerns/u3-frequency.md), [`u4-visualization`](../perspec-me/capiwatt-lens-hackathon/concerns/u4-visualization.md), [`i6-telemetry`](../perspec-me/capiwatt-lens-hackathon/concerns/i6-telemetry.md) e [`i9-integration`](../perspec-me/capiwatt-lens-hackathon/concerns/i9-integration.md)). Este documento **não é a fonte primária de verdade** — é um resumo consolidado da fronteira. Em caso de divergência, as Concern Resolution pages e ADRs vigentes prevalecem.

> **Manutenção:** este arquivo deve ser atualizado sempre que rotas públicas em `/v1/*`, modelos Pydantic de entrada/saída, parâmetros de URL ou regras de orquestração entre frontend e backend forem alterados (novas issues, revisão de concerns ou evolução da camada de API). Ver seção "Como manter em sincronia" no final.

---

## Divisão de posse

- **Frontend (F1)**:
  - É responsável pela apresentação, densidade operacional e renderização de telas (exploração de precedentes, busca textual/semântica, visualização da família documental e versões, grafo egocêntrico de relações, visualização de processo SEI, painéis de cobertura, alertas e digest de e-mail demonstrativo).
  - É responsável pela seleção de usuário da demonstração (`carolina` ou `equipe`), persistindo o usuário ativo em `localStorage` apenas como conveniência de navegação. Com Cognito ativo no `/config.json` (implantação AWS), o seletor some e o usuário vem do login SRP (Amplify Auth); o frontend envia o access token em `Authorization: Bearer`.
  - É responsável pela camada adaptadora de visualização (`appRepository.ts`), que traduz os envelopes brutos retornados pelo backend para as estruturas ricas de exibição da UI.
  - **Nunca acessa diretamente o serviço vetorial (`ai`)**, nem Bedrock, nem instâncias de armazenamento/banco de dados: toda comunicação transita exclusivamente via backend por rotas HTTP `/v1/*`.

- **Backend (F3)**:
  - É o dono do **catálogo documental**: famílias (`document_family`), versões (`document_version`), metadados oficiais e controle de versão mais recente (`face`).
  - É o dono do armazenamento físico de arquivos: serve os textos extraídos normalizados e provê streaming dos PDFs originais (`/v1/document-pdfs/*`).
  - É o dono da camada de **grafo e relações**: persiste arestas explícitas e sugeridas (`document_relations`), resolve tipos de vizinhança (`family` vs. `processo`) e serve subgrafos egocêntricos sem necessidade de chamada externa.
  - É o dono da política de **notificações e telemetria**: armazena a preferência de escopo por usuário (`estrita` ou `ampla`), aplica deduplicação `(user_id, document_version_id)`, gera digests de e-mail e registra eventos de auditoria e abertura (`notification_opened`).
  - Orquestra chamadas ao serviço vetorial (`ai` em `/internal/v1/*`), congelando a lista ordenada de chunks (paginação por cursor), persistindo `SearchExecution` para replay e enriquecendo os resultados de busca com os dados do catálogo antes de responder ao frontend.

---

## Forma do boundary

1. **Protocolo e transporte:** HTTP/1.1 REST sobre JSON (`Content-Type: application/json; charset=utf-8`), exceto para a rota de visualização de arquivos originais que entrega `application/pdf` como stream binário em linha (`content_disposition_type: inline`).
2. **Prefixo de versão:** Todas as rotas públicas do backend utilizam o prefixo `/v1/`. No ambiente de desenvolvimento local, o frontend acessa `/v1/*` através do proxy reverso configurado no Vite para o servidor backend (`http://backend:8000` ou `http://localhost:8000`).
3. **Identificadores com caracteres especiais:** Números de processos SEI (ex.: `48500.001234/2024-11`) contêm barras (`/`).
   - O cliente frontend **sempre** aplica `encodeURIComponent(id)` antes de interpolar o identificador na URL.
   - O servidor FastAPI declara esses parâmetros utilizando a diretiva de conversão `{node_id:path}` do Starlette, permitindo a correta captura do segmento completo decodificado.
4. **Autenticação por modo (`AUTH_MODE`, decidido em [`capiwatt-aws-deploy/i9-integration`](../perspec-me/capiwatt-aws-deploy/concerns/i9-integration.md)):**
   - `AUTH_MODE=none` (padrão; Compose local): não há tokens JWT, cookies de sessão ou cabeçalhos `Authorization`. Identificadores de usuário (`user_id`) trafegam explicitamente como parâmetros de rota (`/v1/users/{user_id}/*`).
   - `AUTH_MODE=cognito` (AWS): todo `/v1/*` exceto `/v1/health` exige `Authorization: Bearer <access token>` do User Pool (validado por JWKS, `client_id`, `token_use`, `exp`). O `user_id` é o claim `username`; o formato das rotas e dos corpos não muda. `/v1/users/{user_id}/*` responde `403` se o caminho divergir do token; `/v1/ingestions` e `/v1/demo/reset` exigem o grupo `admin`.
   - Contas na AWS: `carolina`, `equipe` e `admin` (extras via `.env`), provisionadas por script, sem auto-cadastro; login por usuário ou e-mail `<user_id>@capiwatt.demo`.
5. **Erros e códigos de status:**
   - `200 OK`: Operações de leitura e consultas bem-sucedidas.
   - `401 Unauthorized` (só com `AUTH_MODE=cognito`): token ausente, expirado ou inválido.
   - `403 Forbidden` (só com `AUTH_MODE=cognito`): `user_id` do caminho diferente do token, ou rota administrativa sem o grupo `admin`.
   - `404 Not Found`: Família, nó de grafo, processo ou documento inexistente. O backend retorna `{"detail": "..."}`. O frontend captura e instancia exceções específicas de domínio (`DocumentNotFoundError`, `GraphNodeNotFoundError`, `ProcessoNotFoundError`).
   - `422 Unprocessable Entity`: Validação de esquema do Pydantic falhou (ex.: valor inválido para o voto de feedback ou para o escopo de notificação).
   - `500 Internal Server Error`: Falha interna inesperada. O frontend encapsula em erros genéricos informando o status HTTP retornado.

---

## Operações do port público

| Operação | Método | Rota `/v1/*` | Payload de entrada | Resposta |
|---|---|---|---|---|
| **Health check** | `GET` | `/v1/health` | — | `BackendHealth` |
| **Busca de documentos** | `POST` | `/v1/search` | `{ query: string, top_k?: number, cursor?: string, limit?: number }` | `SearchEnvelope` |
| **Listagem de famílias documentais** | `GET` | `/v1/families` | — | `FamilySummary[]` |
| **Leitura de documento** | `GET` | `/v1/documents/{family_id}` | Query: `?version=string` (opc.) | `DocumentDetail` |
| **Download/abertura de PDF** | `GET` | `/v1/document-pdfs/{document_version}` | — | Stream `application/pdf` |
| **Grafo egocêntrico** | `GET` | `/v1/documents/{node_id:path}/graph` | — | `Graph` |
| **Listagem de processos** | `GET` | `/v1/processos` | — | `ProcessoSummary[]` |
| **Detalhes do processo** | `GET` | `/v1/processos/{processo_id:path}` | — | `Processo` |
| **Parecer demonstrativo** | `GET` | `/v1/opinion` | — | `OpinionData` |
| **Envio de feedback** | `POST` | `/v1/feedback` | `{ request_id, document_version, chunk_index, vote }` | `Feedback` |
| **Consulta de feedback** | `GET` | `/v1/feedback` | Query: `request_id?`, `document_version?`, `chunk_index?`, `family_id?`, `limit?` | `Feedback[]` |
| **Consulta de escopo** | `GET` | `/v1/users/{user_id}/notification-scope` | — | `{ scope: NotificationScope \| null }` |
| **Definição de escopo** | `PUT` | `/v1/users/{user_id}/notification-scope` | `{ scope: "estrita" \| "ampla" }` | `{ scope: NotificationScope }` |
| **Notificações do usuário** | `GET` | `/v1/users/{user_id}/notifications` | — | `NotificationItem[]` |
| **Abertura de notificação** | `POST` | `/v1/notifications/{id}/opened` | — | `{ notification_id: number, opened: true }` |
| **Prévias de e-mail digest** | `GET` | `/v1/users/{user_id}/email-digests` | — | `EmailDigestPreview[]` | **⚠️ Implementado mas não ativado (SES indisponível)** |
| **Auditoria de telemetria** | `GET` | `/v1/notification-events` | Query: `user_id?`, `document_version_id?` | `NotificationEvent[]` | |

---

## Detalhamento das operações

### Catálogo de famílias e parecer demonstrativo (issue #110)

- **`GET /v1/families`** lista as famílias realmente presentes no catálogo após ingestão. Cada item contém `family_id`, `document_id`, `document_type`, `processo_numero: string | null`, `versions_count` e `latest_version_date`; os metadados descritivos vêm da versão face. Lista vazia antes da ingestão. O frontend apresenta cada família como uma peça documental e usa `family_id` para abrir `/documents/{family_id}`.
- **`GET /v1/opinion`** retorna uma ficha demonstrativa para o caso Carolina/MMGD. Exige que os votos Coelba, Cemig e Enel estejam no catálogo; antes disso responde 404. `OpinionData` mantém os campos de apresentação `title`, `processNumber`, `family`, `theme`, `code`, `issuedAt`, `status`, `verdict`, `verdictSummary`, `situation`, `suggestedUnderstanding`, `attentionPoints`, `figures`, `confidence` e `coverage`. Os três textos exibidos são extratos da fixture F3 alinhados com os PDFs do caso; `confidence` e `coverage` são `null`, porque não há medição ou geração de conclusão jurídica. O frontend oculta os indicadores ausentes. O endpoint não representa parecer jurídico automatizado.
- `ApiAppRepository` usa também `GET /v1/processos` e `GET /v1/users/{user_id}/notifications` para os dados de dashboard e notificações. As telas próprias de processos e notificações já consumiam essas rotas diretamente. A vitrine de famílias da exploração usa a listagem HTTP, e o mapa de relações usa `/v1/processos`, `/v1/families` e `/v1/documents/{node_id:path}/graph`.
- No modo Compose (`cognito: null`), o shell espera `POST /v1/ingestions` concluir antes de renderizar as telas do catálogo. Isso evita que a primeira navegação solicite `/v1/opinion` ou detalhes de documentos enquanto o banco ainda está vazio. No modo Cognito, não há espera por essa ingestão, pois a operação exige administrador.

### 1. Diagnóstico e saúde cruzada

- **`GET /v1/health`**
  - **Finalidade:** Permite ao frontend e aos orquestradores verificar a disponibilidade operacional do backend e a conectividade com o serviço de inteligência artificial (`ai`).
  - **Comportamento:** Retorna HTTP 200 contendo `backend: "ok"`. Se o `ai` não estiver acessível, o backend não quebra com 500, respondendo `ai: "unreachable"` para que o frontend tome ação graciosa (ex.: desabilitar busca e disparos de ingestão).
  - **Schema:**
    ```typescript
    export type BackendHealth = {
      backend: string; // "ok"
      ai: string;      // "ok" | "unreachable"
    };
    ```

### 2. Busca e exploração de precedentes

- **`POST /v1/search`**
  - **Finalidade:** Submissão de termos de pesquisa textual/semântica para recuperação dos trechos (chunks) relevantes.
  - **Comportamento (issues #76/#78/#79/#96/#97):** Sem `cursor`, o backend repassa a consulta ao `ai` uma única vez e resolve cada hit no catálogo. Monta um resultado **plano por chunk**: sem agrupar por `family_id` e sem deduplicar por peça. Ordena por `(-score, document_version, chunk_index)`, gera um `request_id` (UUIDv4), congela o conjunto inteiro em `SearchExecution` (`i7-reproducibility`) e devolve a primeira página (`limit`, padrão 10). Com `cursor` (o `next_cursor` da página anterior), devolve a página seguinte do conjunto congelado, sem chamar o `ai`. O `request_id` é o mesmo da primeira página e `query` continua obrigatório no corpo. Cursor inválido → 400. `total` é o número de chunks do conjunto congelado inteiro. `stale_corpus: true` indica que já existe um `corpus_version` mais novo que o da busca. "Mais novo" é o da última ingestão (`DocumentVersion.ingested_at`, issue #97), nunca o maior em ordem lexicográfica: `corpus_version` é o hash do manifesto (#68).
  - **Consumo no frontend (issue #93):** `searchDocuments(query, cursor?)` envia `{ query }` ou `{ query, cursor }`, sem `top_k` nem `limit`. A `SearchPage` exibe um card por chunk, e a `ExplorePage` agrupa os chunks por processo SEI na ordem do backend. As duas telas têm "Carregar mais", que acrescenta a página sem reordenar, e mostram um aviso de `stale_corpus` com "Refazer a busca" ([`u4-visualization`](../perspec-me/capiwatt-lens-hackathon/concerns/u4-visualization.md)). O e2e `test_frontend_search_shape_matches_real_envelope` confere que as chaves do resultado real são exatamente as de `SearchResult`.
  - **Esquema de Entrada:**
    ```typescript
    export type SearchRequest = {
      query: string;
      top_k?: number;   // repassado ao ai; sem ele, o ai usa o seu default (10 no modo real)
      cursor?: string;  // opaco; continuação do conjunto congelado
      limit?: number;   // tamanho da página, padrão 10
    };
    ```
  - **Esquema de Retorno:**
    ```typescript
    export type SearchResult = {
      family_id: string;          // só dado/filtro; não agrupa resultados
      document_version: string;
      chunk_id: string;           // id estável do chunk no índice do ai (#96)
      chunk_index: number;        // índice real do chunk no documento, 0-based (#96)
      excerpt: string;
      score: number;
      localizador: string | null; // extracted_text_locator da DocumentVersion
      document_type: string;
      document_id: string;
      processo_numero: string | null;
      version_date: string;
    };

    export type SearchEnvelope = {
      request_id: string;
      data_mode: string;       // "demo" | "real"
      corpus_version: string;
      model_version: string;
      ranking_version: string; // ex: "demo-ranking-v1"
      results: SearchResult[];
      total: number;
      next_cursor: string | null;
      stale_corpus: boolean;
    };
    ```
  - **Limite conhecido (issue #93, aberta):** o frontend não envia `top_k`, e o `ai` usa 10 por padrão no modo real. Com isso, o conjunto congelado tem no máximo 10 chunks e cabe numa página, e o "Carregar mais" só aparece se o `top_k` subir.

### 3. Leitura e linha do tempo de documentos

- **`GET /v1/documents/{family_id}`**
  - **Finalidade:** Carregar o cabeçalho oficial, o processo de origem, a linha do tempo completa de versões e o texto integral extraído da versão ativa de uma família documental.
  - **Parâmetros:**
    - `family_id` (path): Identificador único da família (ex.: `resolucao-autorizativa-1001-2023`).
    - `version` (query, opcional): `document_version` específica desejada. Se omitida ou se não pertencer à família, o backend seleciona automaticamente a `face` (versão mais recente).
  - **Comportamento:** Se a família não existir, retorna 404 (`detail: "Familia nao encontrada"`). Caso o arquivo de texto extraído (`extracted_text_locator`) não seja encontrado no disco, retorna 404 (`detail: "Texto extraido nao encontrado para esta versao"`). Se existir PDF original associado no corpus demonstrativo, retorna a URL relativa em `source_pdf_url`.
  - **Schema:**
    ```typescript
    export type VersionSummary = {
      document_version: string;
      version_date: string;
      version_date_source: string;
    };

    export type SelectedVersion = VersionSummary & {
      text: string;
    };

    export type DocumentDetail = {
      family_id: string;
      document_id: string;
      document_type: string;
      processo_numero: string | null;
      versions: VersionSummary[];
      selected_version: SelectedVersion;
      source_pdf_url: string | null;
    };
    ```

- **`GET /v1/document-pdfs/{document_version}`**
  - **Finalidade:** Servir o arquivo PDF original associado à versão documental especificada para visualização embutida ou download.
  - **Comportamento:** Resolve o caminho relativo declarado na fixture e entrega o arquivo com `Content-Type: application/pdf`. Se o PDF não existir ou escapar do diretório autorizado, retorna 404.

### 4. Grafo de relações e cadeia de processos

- **`GET /v1/documents/{node_id:path}/graph`**
  - **Finalidade:** Retornar o subgrafo egocêntrico centrado no nó especificado (de raio 1), suportando tanto nós do tipo `family` quanto nós do tipo `processo`.
  - **Comportamento:** O backend inspeciona o catálogo para resolver a natureza do nó (`family` vs. `processo`) e busca todas as arestas em `document_relations` onde o nó participa como origem (`source_id`) ou destino (`target_id`). As arestas retornadas sempre resolvem o `neighbor_id` e `neighbor_kind` do ponto de vista do nó consultado. Se o nó não for encontrado, retorna 404 (`detail: "No nao encontrado"`).
  - **Schema:**
    ```typescript
    export type NodeKind = "family" | "processo";

    export type RelationEvidence = {
      document_version: string;
      locator: string;
    };

    export type GraphEdge = {
      type: string;        // ex: "pertence_ao_processo", "responde_a", "referencia", "similar_a"
      origin: string;      // "explicit" | "similarity"
      status: string;      // "confirmed" | "suggested" (similar_a vinda do ai nasce "suggested")
      neighbor_id: string;
      neighbor_kind: NodeKind;
      evidence: RelationEvidence | null;  // referencia vinda do ai: locator = chunk_id
      score: number | null;              // só em similar_a (issue #92)
    };

    export type Graph = {
      node_id: string;
      node_kind: NodeKind;
      edges: GraphEdge[];
    };
    ```

- **`GET /v1/processos`**
  - **Finalidade:** Listagem resumida de todos os processos SEI mapeados no catálogo, com dados agregados de movimentação para alimentação de tabelas e dashboards.
  - **Comportamento:** Agrupa as arestas `pertence_ao_processo`, computa a data da movimentação mais recente (`latest_movement_at`), a quantidade de peças e a lista ordenada de tipos documentais presentes. Ordena por movimentação decrescente.
  - **Schema:**
    ```typescript
    export type ProcessoSummary = {
      processo_id: string;
      latest_movement_at: string;
      latest_document_type: string;
      latest_document_id: string;
      pieces_count: number;
      document_types: string[];
    };
    ```

- **`GET /v1/processos/{processo_id:path}`**
  - **Finalidade:** Retornar o dossiê detalhado do processo SEI, incluindo a lista cronológica de peças documentais e a malha de causalidade/resposta (`responde_a`) entre elas.
  - **Comportamento:** Retorna as peças ordenadas por `version_date` crescente e as arestas `responde_a` existentes entre as famílias vinculadas ao processo. Se não houver peças associadas, retorna 404 (`detail: "Processo nao encontrado"`).
  - **Schema:**
    ```typescript
    export type ProcessoPiece = {
      family_id: string;
      document_type: string;
      document_id: string;
      version_date: string;
    };

    export type RespondeAEdge = {
      source_family_id: string;
      target_family_id: string;
      evidence: RelationEvidence | null;
    };

    export type Processo = {
      processo_id: string;
      pieces: ProcessoPiece[];
      responde_a: RespondeAEdge[];
    };
    ```

### 5. Avaliação e feedback de relevância

- **`POST /v1/feedback`**
  - **Finalidade:** Registrar a avaliação de utilidade (polegar para cima / polegar para baixo) feita pelo usuário sobre um resultado de busca.
  - **Comportamento:** Associa o voto obrigatoriamente ao `request_id` da busca original e ao chunk avaliado, identificado por `document_version` + `chunk_index` (issue #82; `chunk_index` é o índice real do chunk no documento, o mesmo devolvido em cada resultado de `POST /v1/search` desde a issue #96). `family_id` é opcional no backend, só por compatibilidade legada, e o frontend não o envia (issue #94). Validação estrita: `vote` deve ser `"up"` ou `"down"`, e a falta de `document_version`/`chunk_index` resulta em 422. Nenhum campo de comentário textual é exigido ou aceito.
  - **Alvo do voto no frontend (issues #94/#93):** o voto usa o `document_version` + `chunk_index` do próprio resultado de busca. Na `SearchPage` cada card é um chunk. Na `ExplorePage`, cujo card é um processo, o voto vai para o primeiro trecho do processo na ordem do backend ([`u6-acceptance`](../perspec-me/capiwatt-lens-hackathon/concerns/u6-acceptance.md)).
  - **Schema:**
    ```typescript
    export type Vote = "up" | "down";

    export type FeedbackPayload = {
      request_id: string;
      document_version: string;
      chunk_index: number;
      vote: Vote;
    };

    export type Feedback = {
      id: number;
      request_id: string;
      document_version: string | null;
      chunk_index: number | null;
      family_id: string | null;
      vote: Vote;
      created_at: string;
    };
    ```

- **`GET /v1/feedback`**
  - **Finalidade:** Consulta administrativa de feedbacks coletados (para validação manual da equipe e refinamento dos modelos de ranqueamento).
  - **Parâmetros de Query:** `request_id?` (string), `document_version?` (string), `chunk_index?` (int), `family_id?` (string), `limit?` (int). Retorna lista ordenada pelo id decrescente (`Feedback[]`).

### 6. Notificações, preferências e digest de e-mail

- **`GET /v1/users/{user_id}/notification-scope`**
  - **Finalidade:** Obter a configuração atual de escopo do usuário.
  - **Comportamento:** Retorna `{ scope: "estrita" | "ampla" }` ou `{ scope: null }` caso o usuário ainda não tenha realizado a seleção obrigatória.

- **`PUT /v1/users/{user_id}/notification-scope`**
  - **Finalidade:** Salvar a escolha obrigatória de escopo de notificação do usuário.
  - **Comportamento:** Cria ou atualiza a preferência no banco (`NotificationScopePreference`). Não existe valor padrão (default) implícito; a escolha pelo usuário é obrigatória antes de receber qualquer notificação (`u3-frequency`).
  - **Payload:** `{ scope: "estrita" | "ampla" }`.

- **`GET /v1/users/{user_id}/notifications`**
  - **Finalidade:** Listar o histórico de notificações geradas para o usuário, ordenadas das mais recentes para as mais antigas.
  - **Comportamento:** Enriquece cada notificação com dados de apresentação do catálogo (`document_type`, `document_id`) e com o indicador booleano `opened` (derivado da presença de evento `notification_opened` na telemetria).
  - **Schema:**
    ```typescript
    export type NotificationScope = "estrita" | "ampla";

    export type NotificationReason =
      | { type: "novo_documento" }
      | {
          type: "correlato";
          relation_type: string;
          neighbor_family_id: string;
          neighbor_kind: string;
        };

    export type NotificationItem = {
      id: number;
      user_id: string;
      document_version_id: string;
      family_id: string;
      document_type: string | null;
      document_id: string | null;
      scope_effective: NotificationScope;
      reasons: NotificationReason[];
      ingestion_job_id: string;
      created_at: string;
      opened: boolean;
    };
    ```

- **`POST /v1/notifications/{notification_id}/opened`**
  - **Finalidade:** Telemetria de engajamento quando o usuário clica em um item de notificação na interface.
  - **Comportamento:** Grava idempotentemente um evento de telemetria `notification_opened` com payload `{ origin: "home" }`. Retorna `{ notification_id: number, opened: true }`. Retorna 404 se a notificação não existir.

- **`GET /v1/users/{user_id}/email-digests`**
  - **Finalidade:** Consultar os digests de e-mail agrupados gerados por job de ingestão para o usuário.
  - **⚠️ Implementado mas não ativado (out of scope operacional).** O código do port `Mailer`, do adapter `PreviewMailer` e desta rota está completo e testado, mas o canal de e-mail **não é usado** neste ciclo porque o SES não foi disponibilizado pela organização do hackathon. A rota retorna lista vazia ou os digests gerados pelo adapter de prévia (se a geração de digest estiver habilitada no código). O código permanece como evidência do trabalho realizado.
  - **Schema:**
    ```typescript
    export type EmailDigestPreview = {
      email_id: string;
      user_id: string;
      ingestion_job_id: string;
      notification_ids: number[];
      rendered_body: string;
      created_at: string;
    };
    ```

- **`GET /v1/notification-events`**
  - **Finalidade:** Auditoria e observabilidade do ciclo de vida das notificações (geração, supressão por deduplicação, entrega e abertura), conforme especificado em `i6-telemetry`.
  - **Parâmetros de Query:** `user_id?` (string, opcional), `document_version_id?` (string, opcional).
  - **Schema:**
    ```typescript
    export type NotificationEvent = {
      id: number;
      event_type: string; // "notification_generated" | "notification_suppressed" | "email_digest_generated" | "notification_delivered_home" | "notification_delivered_email" | "notification_opened"
      user_id: string;
      document_version_id: string | null;
      notification_id: number | null;
      email_id: string | null;
      payload: Record<string, unknown> | null;
      created_at: string;
    };
    ```

---

## Operações administrativas e de demonstração

| Operação | Método | Rota `/v1/*` | Resposta | Descrição |
|---|---|---|---|---|
| **Disparo de ingestão** | `POST` | `/v1/ingestions` | `DemoIngestion` | Ingestão do corpus demo e relações no Postgres e no `ai`. |
| **Reset da demonstração** | `POST` | `/v1/demo/reset` | `DemoResetReport` | Purga dados de interação de visitantes, mantendo o catálogo base. |

- **`POST /v1/ingestions`**
  - Executa a carga das fixtures (`demo_corpus.json` e `demo_relations.json`), indexa chunks no serviço vetorial, realiza upsert no banco e dispara `run_notifications` para usuários com escopo ativo.
  - Retorno:
    ```typescript
    export type DemoIngestion = {
      ingestion_job_id: string;
      families_count: number;
      versions_count: number;
      relations_count: number;
    };
    ```

- **`POST /v1/demo/reset`**
  - Remove apenas os registros dinâmicos gerados por visitantes (`notification_events`, `email_digests`, `notifications`, `notification_scope_preferences`, `feedback`, `search_executions`). O catálogo documental, textos extraídos e arestas permanecem intactos.
  - Retorno:
    ```typescript
    export type DemoResetReport = {
      deleted: Record<string, number>;
    };
    ```

---

## Teste de contrato e costuras (seams)

A fronteira é protegida em dois níveis complementares:

1. **Costura no Frontend (`hackathon/frontend/src/api/` e `services/appRepository.ts`):**
   - O frontend centraliza todas as requisições HTTP nos módulos `src/api/*`.
   - A camada de visualização utiliza `AppRepository` e `ApiAppRepository` para adaptar os envelopes HTTP aos componentes. Os testes unitários interceptam `fetch`; a execução do produto não usa `MockAppRepository` nem fixtures de produto no navegador.
   - Testes de componentes (Vitest + React Testing Library) interceptam as chamadas no nível de rede/fetch, garantindo que cabeçalhos, rotas e códigos de erro sejam tratados de forma idêntica ao comportamento do backend.

2. **Costura no Backend (`hackathon/backend/tests/`):**
   - Testes de integração FastAPI utilizam `httpx.AsyncClient` e `TestClient(app)` para exercitar as rotas públicas `/v1/*`.
   - As dependências de banco (`get_db_session`) e do cliente vetorial (`get_ai_client`) são sobrescritas via `app.dependency_overrides`, permitindo testar contratos HTTP ponta a ponta sem instâncias externas de banco ou AWS.

---

## Como manter em sincronia

1. Toda proposta de alteração neste contrato (novas rotas, alteração de modelos Pydantic/TypeScript, novos campos de telemetria ou mudanças na navegação de busca/processos) deve nascer ou ser discutida no contexto das Concern Resolution pages correspondentes em `requirements/perspec-me/capiwatt-lens-hackathon/concerns/` (ex.: `u4-visualization`, `u3-frequency`, `i9-integration`).
2. Quando uma Concern Resolution page for atualizada ou novas rotas forem introduzidas em `hackathon/backend/app/routes/` ou `hackathon/frontend/src/api/`, atualize este arquivo mantendo a representação do estado **vigente**.
3. Atualize o metadado `last_synced_with_sources` no frontmatter com a data do ajuste.
