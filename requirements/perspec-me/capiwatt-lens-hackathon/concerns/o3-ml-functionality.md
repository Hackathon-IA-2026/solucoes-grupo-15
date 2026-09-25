---
concern_id: o3-ml-functionality
concern: skills/in-progress/perspec-me/catalog/concerns/o3-ml-functionality/README.md
perspective: system-objectives
status: resolved
topics:
  - issue-27 — Qual é o contrato do parecer jurídico conclusivo de uma frase e como ele permanece verificável?
updated_at: 2026-09-25
---

## Current resolution

O parecer conclusivo do TB1 é um **objeto estruturado por processo** — não por documento individual, e não uma frase de texto livre. Um processo agrupa múltiplos documentos (movimentos, petições, decisões, etc.) em um **cluster**. A frase é derivada dos campos, nunca a fonte da verdade.

O objeto tem **seis campos principais**:

| Campo | Prioridade visual | Uso principal | Descrição |
|-------|-------------------|---------------|-----------|
| **Status do processo** | Alta (fonte maior) | Front + Back | Enum com a conclusão jurídica do processo (sempre obrigatório) |
| **Agente** | Média | Front + Back | Nome da empresa/entidade extraído por LLM (pode ser vazio) |
| **Tipo de agente** | Média | Front + Back | Classificação do agente: transmissora, geradora, etc. (pode ser vazio) |
| **Headline** | Baixa (fonte menor) | Front + Back | Resumo curto gerado por LLM, máx. 80 chars |
| **Número de documentos** | Info | Front | Quantidade de documentos no cluster |
| **Metadados do cluster** | Técnico | Back | Lista de documentos com detalhes (document_id, tipo, data, etc.) |

### Campo 1: Status do processo (prioridade máxima, sempre obrigatório)
Enum com a conclusão jurídica. Valores confirmados: `advertencia_mantida`, `advertencia_anulada`, `multa_mantida`, `multa_reduzida` (com valores `de x para y`), `multa_convertida_em_advertencia`, `multa_aumentada`, `processo_arquivado`, `provimento_parcial`, `abstencao` (quando o processo não traz advertência nem multa), e `inconclusivo` (quando não foi possível determinar o status). **Um status por processo. Sempre obrigatório — nunca vazio.**

### Campo 2: Agente (prioridade média)
**Texto extraído por LLM** com o nome da empresa ou entidade do processo. Exemplos: `Taesa`, `Furnas`, `AxiaNorte`, `ABRACE`, `Enel`, `CEMIG`. **Um agente por processo. Pode ser vazio se não identificado.**

### Campo 3: Tipo de agente (prioridade média)
Classificação do agente extraída por LLM. Valores possíveis: `transmissora`, `geradora`, `associação`, `comercializadora`, `distribuidora`, `consumidor`. **Um tipo por processo. Pode ser vazio se não identificado.**

### Campo 4: Headline (prioridade menor)
Resumo curto para o advogado captar o processo "de bater o olho". **Um headline por processo, máximo 80 caracteres.** Deve complementar o status, evitando repetir informações já presentes nele sem adicionar contexto. Exemplos:
- status = `multa_reduzida de 2.000.000 para 500.000 reais` → headline = `após 1 ano de processo jurídico a multa foi reduzida`
- status = `multa_mantida` → headline = `mesmo recorrendo judicialmente por 6 meses a multa se manteve`

Gerado por LLM (Bedrock), não persistido em banco no MVP.

### Campo 5: Número de documentos do cluster (informativo)
Quantidade de documentos que compõem o processo. **Exibido no front** para dar contexto ao usuário sobre o tamanho/complexidade do processo.

### Campo 6: Metadados do cluster (técnico, backend)
Lista detalhada dos documentos do processo, com metadados de cada um:
- `document_id`
- Tipo do documento (petição, decisão, recurso, etc.)
- Data
- Outros metadados relevantes

**Uso principal no backend** para rastreabilidade, evidence_ref e operações internas.

### Gates de erro
Cada campo tem **categoria de erro própria** para tracking de métricas de eficácia:
- `erro_status` — erro no status do processo (mais grave)
- `erro_agente` — erro no nome do agente
- `erro_tipo_agente` — erro no tipo de agente
- `erro_headline` — erro no headline
- `erro_cluster` — erro no agrupamento de documentos (menos grave)

A arquitetura deve facilitar adição de novos campos e gates sem retrabalho estrutural.

A redação da peça jurídica completa continua fora do TB1 (decisão herdada de #12/#14).

## Confirmed facts

- (2026-09-25, usuário) A classe principal do parecer é **discreta** (um Enum), chamada **status do processo**.
- (2026-09-25, rodada 8, validação com Carolina) **Granularidade é por processo, não por documento.** Um processo agrupa múltiplos documentos (movimentos) em um cluster. O parecer retorna status, responsável e headline **por processo**.
- Valores do Enum de status do processo: advertência mantida; advertência anulada; multa mantida; multa reduzida (de x para y); multa convertida em advertência; multa aumentada; processo arquivado; provimento parcial; abstenção (vazio — processo sem advertência nem multa).
- O campo de texto livre existe, mas é **terciário** — um headline/resumo curto, não a conclusão formal.
- (2026-09-25, rodada 5) **Um status, um responsável e um headline por processo.**
- (2026-09-25, rodada 5) O headline deve **complementar** o status, evitando repetir informações já presentes nele sem adicionar contexto. Exemplos:
  - status = `multa_reduzida de 2.000.000 para 500.000 reais` → headline = `após 1 ano de processo jurídico a multa foi reduzida`
  - status = `multa_mantida` → headline = `mesmo recorrendo judicialmente por 6 meses a multa se manteve`
- (2026-09-25, rodada 6) **Limite do headline: máximo de 80 caracteres.**
- (2026-09-25, rodada 6) **Evidence ref:** status, responsável e headline devem carregar um `evidence_ref` com `document_id` + `page`/`chunk_id` + **trecho de texto** (chunk) que comprova a afirmação. No front, o usuário pode clicar em um ícone (?) para ver esses trechos de evidência.
- (2026-09-25, rodada 7) **Campo: responsável** — **texto extraído por LLM** (não Enum) com nome da empresa + tipo de agente entre parênteses (transmissora, geradora, associação, comercializadora, distribuidora, consumidor). Prioridade visual média, prioridade de assertividade alta (entre status e headline).
- (2026-09-25, rodada 8) **Responsável não é Enum** — universo de empresas é grande demais. Extração via LLM (Bedrock). Formato: `NomeEmpresa (tipo)`. Exemplos: `Taesa (transmissora)`, `Furnas (geradora)`, `AxiaNorte (transmissora)`.
- (2026-09-25, rodada 7) **Hierarquia de prioridade visual (tamanho da fonte):** status (maior) > responsável (médio) > headline (menor).
- (2026-09-25, rodada 7) **Hierarquia de prioridade de assertividade:** status (máxima — evitar erro a todo custo) > responsável (alta) > headline (moderada).
- (2026-09-25, rodada 7) **Gates de erro separados por campo:** `erro_status`, `erro_agente`, `erro_tipo_agente`, `erro_headline`, `erro_cluster`. Cada categoria é rastreada independentemente para monitoramento de métricas de eficácia do sistema.
- (2026-09-25, rodada 7) Arquitetura deve facilitar adição de novos campos e gates sem retrabalho estrutural.
- (2026-09-25, rodada 8) **Novo campo: número de documentos do cluster** — exibido no front para dar contexto sobre tamanho/complexidade do processo.
- (2026-09-25, rodada 8) **Novo campo: metadados do cluster** — lista detalhada dos documentos do processo (document_id, tipo, data, etc.). Uso principal no backend para rastreabilidade e operações internas.
- (2026-09-25, rodada 2) **TB1 cobre só processos punitivos** (caso Carolina/MMGD). Outros tipos ficam para iterações futuras.
- (2026-09-25, rodada 2) A arquitetura de parecer deve ser **expansível**: novos Enums e campos para outros tipos de processo podem ser adicionados sem reescrever a estrutura base.
- (2026-09-25, rodada 3) **Valores adicionais do Enum punitivo aprovados:** `multa_aumentada`, `processo_arquivado`, `provimento_parcial`. Nenhum valor adicional pode ser inserido sem consentimento explícito do usuário.
- (2026-09-25, rodada 3) O headline é **texto mais livre**, capaz de expressar qualquer conclusão processual (inclusive não-punitivas), mas sempre derivado de evidência documental.
- (2026-09-25, rodada 4) O headline (resumo do que o usuário quer ver no processo) é **gerado por LLM via Bedrock**, não por seleção de lista fixa.
- (2026-09-25, rodada 4) **Sem persistência do headline em banco/cache no MVP** — o headline pode variar conforme a pergunta do usuário e atualizações do documento; foco é bom funcionamento do caso de uso inicial, não escalabilidade prematura.
- (2026-09-25, rodada 4) Arquitetura deve seguir boas práticas para facilitar adição de cache/persistência depois, se necessário.

## Decisions

- 2026-09-25 (issue-27, usuário): o parecer é um objeto estruturado; a frase é derivada dos campos, não a fonte da verdade.
- 2026-09-25 (issue-27, usuário): o campo primário é um Enum discreto chamado **status do processo**, com um valor de abstenção quando o processo não contém advertência nem multa.
- 2026-09-25 (issue-27, usuário): o headline em texto livre é campo terciário, complementar ao status.
- 2026-09-25 (issue-27, usuário, rodada 2): **escopo TB1 = processos punitivos apenas** no campo primário (Enum de advertência/multa). Headline pode acomodar outros tipos de conclusão, mas o campo discreto do TB1 não precisa cobrir concessão, leilão, outorga, etc.
- 2026-09-25 (issue-27, usuário, rodada 2): a arquitetura deve ser **expansível** — adicionar novos Enums e formatos para outros tipos de processo deve ser "fácil" depois, sem retrabalho estrutural.
- 2026-09-25 (issue-27, usuário, rodada 3): novos valores do Enum punitivo aprovados: `multa_aumentada`, `processo_arquivado`, `provimento_parcial`. **Qualquer adição futura requer consentimento explícito do usuário.**
- 2026-09-25 (issue-27, usuário, rodada 3): headline = texto livre (não Enum), capaz de expressar conclusões punitivas e não-punitivas, mas sempre vinculado a evidência documental.
- 2026-09-25 (issue-27, usuário, rodada 3): a arquitetura deve centralizar o Enum em um único módulo; o restante do código consome o Enum de forma genérica, permitindo que extensões futuras sejam feitas apenas alterando o módulo de definições.
- 2026-09-25 (issue-27, usuário, rodada 4): headline gerado por LLM (Bedrock), não selecionado de lista fixa.
- 2026-09-25 (issue-27, usuário, rodada 4): **MVP sem persistência de headline** — não salvar em banco/cache; headline pode variar por pergunta do usuário ou atualização do documento. Foco em funcionamento do caso de uso, não em escalabilidade prematura. Arquitetura deve permitir adicionar cache depois com facilidade.
- 2026-09-25 (issue-27, usuário, rodada 5): renomeado campo primário para **status do processo**.
- 2026-09-25 (issue-27, usuário, rodada 5): **um status, um agente, um tipo de agente e um headline por processo**.
- 2026-09-25 (issue-27, usuário, rodada 5): headline deve **complementar** o status, não repetir informações já presentes nele sem adicionar contexto.
- 2026-09-25 (issue-27, usuário, rodada 6): **headline limitado a 80 caracteres**.
- 2026-09-25 (issue-27, usuário, rodada 6): **evidence_ref obrigatório** para status, agente e headline — cada um carrega `document_id` + `page`/`chunk_id` + trecho de texto (chunk) que comprova a afirmação. No front, o usuário pode clicar em ícone (?) para ver os trechos de evidência.
- 2026-09-25 (issue-27, usuário, rodada 7): **campos: agente e tipo de agente** — **texto extraído por LLM** (não Enum). Agente = nome da empresa (ex.: Taesa, Furnas). Tipo de agente = classificação (transmissora, geradora, associação, comercializadora, distribuidora, consumidor). Podem ser vazios se não identificados.
- 2026-09-25 (issue-27, usuário, rodada 7): **hierarquia de prioridade visual (tamanho da fonte):** status (maior) > agente/tipo (médio) > headline (menor).
- 2026-09-25 (issue-27, usuário, rodada 7): **hierarquia de prioridade de assertividade:** status (máxima) > agente/tipo (alta) > headline (moderada).
- 2026-09-25 (issue-27, usuário, rodada 7): **gates de erro separados por campo:** `erro_status`, `erro_agente`, `erro_tipo_agente`, `erro_headline`. Cada categoria é rastreada independentemente para monitoramento de métricas de eficácia. Arquitetura deve facilitar adição de novos campos e gates.
- 2026-09-25 (issue-27, usuário, rodada 9): **status do processo é sempre obrigatório** — nunca vazio. Se não for possível determinar, usar `inconclusivo`.
- 2026-09-25 (issue-27, usuário, rodada 9): adicionado `inconclusivo` ao Enum de status do processo.
- 2026-09-25 (issue-27, usuário, rodada 8, validação com Carolina): **granularidade é por processo, não por documento**. Um processo agrupa múltiplos documentos (movimentos) em um cluster.
- 2026-09-25 (issue-27, usuário, rodada 8): **novo campo: número de documentos do cluster** — exibido no front para contexto.
- 2026-09-25 (issue-27, usuário, rodada 8): **novo campo: metadados do cluster** — lista detalhada dos documentos (document_id, tipo, data, etc.). Uso principal no backend.

## Derived requirements and constraints

- O campo primário (status do processo) deve ser um tipo enumerado fechado; `multa_reduzida` precisa carregar os valores inicial e final (`de x para y`).
- O estado `abstencao` do status do processo deve ser explícito e distinto de "não avaliado" — o sistema abstém-se quando não localiza advertência nem multa.
- O headline deve ser derivável das evidências recuperadas e não pode afirmar conclusão que não esteja sustentada por documento.
- **Headline limitado a 80 caracteres.**
- Cada status, agente e headline precisa carregar um `evidence_ref` com:
  - `document_id`
  - `page` e/ou `chunk_id`
  - **trecho de texto** (chunk) que comprova a afirmação
- O modelo de dados do parecer deve ser **genérico** o suficiente para acomodar novos tipos de processo: um campo `tipo_processo` ou `schema_version` pode selecionar qual Enum de status se aplica; em TB1 o único valor relevante é `punitivo`.
- Deve ser possível estender os Enums sem quebrar compatibilidade retroativa (casos já rotulados seguem válidos).
- **Enum centralizado:** todas as definições do Enum de status do processo vivem em um único módulo (ex.: `hackathon/backend/app/enums.py` ou `hackathon/ai/app/enums.py`). O restante do código importa e consome esse Enum de forma genérica — sem hard-code de valores fora do módulo.
- Enum de status do processo TB1 (lista fechada, extensão requer aprovação explícita):
  - `advertencia_mantida`
  - `advertencia_anulada`
  - `multa_mantida`
  - `multa_reduzida` (com campos auxiliares `valor_original` e `valor_final`)
  - `multa_convertida_em_advertencia`
  - `multa_aumentada`
  - `processo_arquivado`
  - `provimento_parcial`
  - `abstencao` (processo sem advertência nem multa)
  - `inconclusivo` (não foi possível determinar o status)
- **Agente e tipo de agente são texto extraído por LLM** — podem ser vazios se não identificados.
- Tipos de agente possíveis: transmissora, geradora, associação, comercializadora, distribuidora, consumidor.
- **Status do processo é sempre obrigatório** — nunca vazio. Se não for possível determinar, usar `inconclusivo`.
- **Cluster de documentos por processo:**
  - `num_documentos` (int) — quantidade de documentos no cluster, exibido no front
  - `metadados_cluster` (lista) — detalhes de cada documento (document_id, tipo, data, etc.), uso principal no backend
- **Gates de erro separados por campo** para tracking de métricas de eficácia:
  - `erro_status` — erro no status do processo (mais grave, prioridade de evitar máxima)
  - `erro_agente` — erro no nome do agente (gravidade média)
  - `erro_tipo_agente` — erro no tipo de agente (gravidade média)
  - `erro_headline` — erro no headline
  - `erro_cluster` — erro no agrupamento de documentos (menos grave)
- Arquitetura deve facilitar adição de novos campos e gates sem retrabalho estrutural.

## Open questions

(Nenhuma — design concept concluído.)

## Evidence

- Issue #27 — pergunta original do contrato do parecer.
- `requirements/perspec-me/capiwatt-lens-hackathon/concerns/u8-cost.md` — erro material, exigência de evidência por campo e regra de abstenção; menção a PydanticAI (não escolhido).
- `hackathon/data/case-1-carolina-mmgd/README.md` — "informações que tornam o resultado relevante" e "erro material".
- Resposta do usuário em 2026-09-25 (rodada 1 do resolve #27) — definição do campo discreto primário e do headline secundário.

## Topic history

- issue-27 (rodada 1): definiu a forma do parecer (objeto estruturado com Enum primário + headline secundário) e reformatou o headline.
- issue-27 (rodada 2): fechou escopo TB1 = punitivo; arquitetura deve ser expansível.
- issue-27 (rodada 3): adicionou `multa_aumentada`, `processo_arquivado`, `provimento_parcial` ao Enum; definiu headline como texto livre derivado de evidência; exigiu Enum centralizado em módulo único.
- issue-27 (rodada 4): headline gerado por LLM (Bedrock), sem persistência no MVP; foco em funcionamento, não escalabilidade prematura; arquitetura deve permitir cache depois.
- issue-27 (rodada 5): renomeado campo primário para **status do processo**; definido que cada processo tem seu próprio conjunto de campos; headline deve complementar o status, não repetir.
- issue-27 (rodada 6): **headline limitado a 80 caracteres**; **evidence_ref obrigatório** — `document_id` + `page`/`chunk_id` + trecho de texto que comprova a afirmação.
- issue-27 (rodada 7): **campos agente e tipo de agente** (separados); **hierarquia de prioridade visual** (status > agente/tipo > headline) e **de assertividade**; **gates de erro separados por campo** (`erro_status`, `erro_agente`, `erro_tipo_agente`, `erro_headline`).
- issue-27 (rodada 8, validação com Carolina): **granularidade é por processo, não por documento**. Um processo agrupa múltiplos documentos (movimentos) em um cluster. Novos campos: **número de documentos do cluster** (front) e **metadados do cluster** (backend).
- issue-27 (rodada 9): **agente e tipo de agente são campos separados**, texto extraído por LLM (não Enum), podem ser vazios. **Status do processo é sempre obrigatório** — adicionado `inconclusivo` ao Enum. **Design concept concluído.**
