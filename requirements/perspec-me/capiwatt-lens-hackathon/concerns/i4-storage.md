---
concern_id: i4-storage
concern: ~/.claude/skills/perspec-me/catalog/concerns/i4-storage/README.md
perspective: infrastructure
status: partial
topics:
  - issue-2 — Qual é o contrato da interface do serviço vetorial (indexar, buscar, agrupar versões) que isola o Bedrock do resto do backend?
  - issue-4 — Como as relações entre documentos são representadas (arestas, origem: metadado explícito vs. similaridade) e onde ficam armazenadas?
  - issue-15 — O backend (F3) deve ser dono também do armazenamento documental, junto das arestas, para que grafo e leitura de documentos não atravessem HTTP, dado um corpus da ordem de 100 documentos?
  - issue-8 — O que roda local e o que roda na AWS no primeiro ciclo, e como o ambiente local fala com Bedrock e SES (credenciais, custo)?
updated_at: 2026-09-18
---

## Current resolution

**Store concreto (issue-8, Eduardo, 2026-09-18): Postgres em container no Compose** para todo o catálogo (famílias, versões, metadados, localizadores, `processo`, fusões, `document_relations`, feedback); DynamoDB (plano l.74) descartado. A consulta de grafo por profundidade (`/v1/documents/{id}/graph`) é servida por CTE recursiva sobre `document_relations`. Originais e texto extraído: volume Docker compartilhado entre `backend` e `ai` no primeiro ciclo (S3 só no M4). Credenciais/AWS: ver [[i2-model-serving]].

**Revisão (issue-15, Eduardo, 2026-09-18) — supersede a parte "serviço vetorial é dono de todo o armazenamento documental" abaixo.** Divisão vigente:

- O **backend (F3) é dono do catálogo documental**: famílias, versões, metadados (checksum, data de coleta, origem, `version_date`), localizador do original e do texto extraído (volume local / S3), nó `processo`, sugestões de fusão (#3), `document_relations` (#4) e feedback. Nós e arestas do grafo vivem no **mesmo store**; `GET /v1/documents/{id}` e `/v1/documents/{id}/graph` são servidos em processo, sem atravessar `/internal/v1/*`.
- O **serviço vetorial (`ai`, F2) é dono só do derivado**: extração de texto, chunking, embeddings, índice vetorial, `references` e `similar_families`. O índice **nunca é fonte de verdade** — é reconstruível a partir do catálogo via `reindex` (#2). `family_id` e `document_version` aparecem no índice apenas como atributos de filtro.
- Texto extraído: o `ai` extrai durante `index` e **escreve num localizador** (volume/S3) que o backend só registra no catálogo — não devolve o texto no `IndexReport`. Racional: OCR/Textract (Fog) produz artefatos grandes e fica do lado de F2.
- **Escala não decide**: um corpus da ordem de 100 documentos (poucos milhares de chunks) é pequeno para qualquer componente — Bedrock, OpenSearch ou um SQLite no backend. O que decidiu foi coerência (nós e arestas juntos; uma só máquina de curadoria no backend) e custo de desenvolvimento no hackathon.

O que segue foi a resolução de issue-2/issue-4 e permanece válido onde não contradiz o acima (forma de `document_relations`, nó `processo`, interface própria do repositório de relações, S3/OpenSearch como destinos físicos).

---

O **serviço vetorial é dono de todo o armazenamento documental**: originais, texto extraído, chunks com metadados e vetores/índice (decisão de Eduardo, 2026-09-18). O backend (F3) não guarda documentos; ele guarda estado de jobs, feedback e eventos. Consequência: o port ([[i9-integration]]) expõe `get_document(document_id, version) → DocumentVersion` — metadados + texto extraído + localizador/URL do original (não os bytes inline); `GET /v1/documents/{id}?version=` do backend proxia essa operação (decisão de Eduardo, 2026-09-18).

Onde fisicamente: originais em volume local / S3 na AWS (plano linha 77); vetores em OpenSearch ([[i2-model-serving]]). Detalhes (bucket vs. volume, layout de chaves) ficam para a issue #8.

**As arestas do grafo de relações moram no backend (F3)**, numa tabela `document_relations` no mesmo store que já guarda as sugestões de fusão de família (#3) — **não em Neptune** no primeiro ciclo (plano: evolução) e **não dentro do serviço vetorial** (decisão de Eduardo, 2026-09-18). O serviço vetorial contribui só os *candidatos*: o resultado de `index` devolve `references` (identificador bruto, tipo classificado quando houver, localizador) e o port ganha `similar_families(family_id, top_k)`; o backend resolve identificadores em `family_id`, grava as arestas com status/autoria e serve o grafo à interface (`/v1/documents/{id}/graph`). Racional: o grafo é um artefato curado (status, confirmação humana, autoria), como a sugestão de fusão; uma só máquina de curadoria, no backend, e o port vetorial continua trocável — Neptune, se vier, substitui o repositório de relações do backend, não o serviço vetorial. Trade-off aceito: documentos num serviço e arestas noutro obriga a resolver ids pela fronteira `/internal/v1/*` ao montar o grafo.

## Confirmed facts

- 2026-09-18 (issue-15, hipótese de Eduardo, "muito provavelmente"): os ~100 documentos do caso 1 são o corpus de avaliação contra o gabarito de priorização, não o volume de produção.

- Plano (linha 77): "S3 de originais e versões" sob F2; volume local antes da migração.
- Plano (linha 118): documentos → S3, vetores → OpenSearch.
- Plano (linha 162): checksum, data de coleta e origem por documento; "versão documental, versão do objeto armazenado e vigência jurídica são atributos distintos"; chunk herda a versão documental.

## Decisions

- 2026-09-18 (issue-8): store do catálogo = Postgres em container no Compose, atrás dos repositórios com interface própria; DynamoDB descartado; grafo por profundidade via CTE recursiva.
- 2026-09-18 (issue-15): o backend é dono do catálogo documental (famílias, versões, metadados, localizadores de original e texto extraído) junto das arestas e do nó `processo`; o `ai` é dono só do índice derivado. **Supersede** a decisão de issue-2 "o serviço vetorial é dono do armazenamento de documentos" e o trade-off de issue-4 "resolver ids pela fronteira HTTP ao montar o grafo".
- 2026-09-18 (issue-15): texto extraído é escrito pelo `ai` num localizador (volume/S3) registrado no catálogo do backend, não devolvido inline.
- 2026-09-18 (issue-15): a escala do corpus (~100 documentos) não é critério para esta divisão; nenhum componente precisa ser dimensionado por ela no primeiro ciclo.

- 2026-09-18 (issue-2): o serviço vetorial é dono do armazenamento de documentos (originais + extraídos), não apenas dos vetores.
- 2026-09-18 (issue-2): `get_document` devolve metadados + texto extraído + ponteiro para o original, nunca o binário inline.
- 2026-09-18 (issue-4): arestas do grafo de relações são armazenadas pelo backend (F3), tabela `document_relations`, junto das sugestões de fusão; não em Neptune nem no serviço vetorial no primeiro ciclo.
- 2026-09-18 (issue-4): o serviço vetorial só entrega candidatos (`references` no resultado de `index`; `similar_families` no port); o backend é dono das arestas.

## Derived requirements and constraints

- 2026-09-18 (issue-15): o catálogo do backend ganha as entidades `document_family` e `document_version` (metadados + `original_locator` + `extracted_text_locator`), no mesmo store de `document_relations` e das sugestões de fusão; store concreto continua na issue #8.
- 2026-09-18 (issue-15): o índice vetorial é derivado — qualquer divergência entre índice e catálogo se resolve por `reindex(corpus_version)`, nunca pelo caminho inverso.
- 2026-09-18 (issue-15): `get_document` deixa de ser operação do port ([[i9-integration]]); a página do documento (#5) lê metadados do catálogo e o texto extraído pelo localizador.

- O port tem `get_document(document_id, version)`; o original é servido por localizador/URL (volume local ou S3), não pelo corpo da resposta.
- Armazenamento de originais e índice vetorial são dois componentes atrás do mesmo port; ambos trocáveis (volume↔S3, OpenSearch↔pgvector) sem mudar o contrato.
- Todo documento entregue pela Carolina é indexado e, portanto, armazenado pelo serviço (Map issue #1).
- `document_relations` (backend): `(source_id, source_kind: family|processo, target_id, target_kind, target_external_ref?, type, origin: explicit|similarity, status: confirmed|suggested|rejected, evidence: {document_version, locator}?, score?, created_at, decided_by?, decided_at?)`; chave única por `(source, target, type)`. `target_external_ref` guarda o identificador citado quando o alvo não está no corpus (aresta pendente de alvo).
- Nós de tipo `processo` são entidade do backend (número SEI + metadados mínimos), não documento do serviço vetorial.
- O repositório de relações fica atrás de uma interface própria no backend (arquitetura limpa), para que Neptune possa substituí-lo depois sem tocar no serviço vetorial.

## Open questions

- (issue-15, respondida 2026-09-18) "~100 documentos" — hipótese de Eduardo: é o corpus de **avaliação** (popular o store e verificar se a busca recupera o ranking ideal do gabarito da Carolina, issue #11), não o teto do corpus em produção. Consequência: o store concreto (#8) não deve ser dimensionado nem escolhido assumindo ~100 documentos como limite; a divisão catálogo/índice de issue-15 não muda.

- (issue-8, respondida 2026-09-18) Store concreto: Postgres no Compose; grafo por CTE recursiva.
- (issue-8, respondida 2026-09-18) Localizadores físicos: volume Docker compartilhado no primeiro ciclo; layout de chaves (`<family_id>/<document_version>/original.<ext>` e `.../extracted.txt`) fica a cargo da implementação do `ai`, não é decisão de especificação.

## Evidence

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 77, 102, 118, 129, 162.

## Topic history

- issue-8: fixou Postgres em container como store do catálogo e volume compartilhado como localizador físico no primeiro ciclo.
- issue-15: moveu o catálogo documental (famílias, versões, metadados, localizadores) do serviço vetorial para o backend, junto das arestas; o `ai` ficou só com o índice derivado; escala (~100 docs) registrada como não decisiva.

- issue-4: colocou as arestas do grafo de relações no backend (`document_relations`), com o serviço vetorial só como fonte de candidatos; definiu a forma da aresta e o nó `processo`.
- issue-2: fixou o serviço vetorial como dono do armazenamento documental além dos vetores, e `get_document` como a operação de leitura do port.
