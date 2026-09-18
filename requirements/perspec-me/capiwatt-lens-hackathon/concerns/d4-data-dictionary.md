---
concern_id: d4-data-dictionary
concern: ~/.claude/skills/perspec-me/catalog/concerns/d4-data-dictionary/README.md
perspective: data
status: partial
topics:
  - issue-3 — Como uma família de versões de um documento é identificada e agrupada num único objeto, na ingestão e no resultado da busca?
updated_at: 2026-09-18
---

## Current resolution

O dicionário de dados do caso 1 separa três conceitos que o plano já dizia serem distintos (linha 162) e que a reunião de 2026-09-17 exigiu tratar como um único objeto na interface:

- **Família** (`family_id`) — a identidade lógica de um documento: "a REN 1000/2021", "o Auto de Infração nº X", "a Decisão Y". É o objeto que o usuário vê como *um* documento.
- **Versão** (`document_version`) — uma instância concreta de uma família: identificada pelo checksum do arquivo original, com data da versão e ordinal dentro da família. Chunks e vetores pertencem a uma versão, nunca à família diretamente.
- **Vigência** (`valid_from`, `valid_to`, `applicability_status`) — atributo de uma versão, nunca da família.

**Processo SEI não é uma família** (decisão de Eduardo, 2026-09-18): um processo é um conjunto de peças distintas ligadas pela relação "pertence ao processo", modelada como aresta do grafo de relações (issue #4). Família de versões aplica-se somente à **mesma peça** republicada, retificada ou consolidada.

**Identificação de família na ingestão, em duas camadas:**

1. **Chave explícita** derivada de metadados — `tipo documental + identificador oficial` (número da norma, número do auto, número do processo + identificação da peça). Quando existe, é determinística e vence sempre.
2. **Similaridade** como fallback, **que apenas sugere, nunca agrupa sozinha** (decisão de Eduardo, 2026-09-18): checksum idêntico ⇒ mesma versão, descartada pela idempotência do `index` (issue #2); texto quase idêntico acima de um limiar ⇒ registra-se uma *sugestão* de que os dois documentos são versões da mesma família, que fica pendente até alguém confirmar. Até a confirmação, os documentos permanecem famílias separadas. Nunca se sugere família entre dois documentos que têm chaves explícitas diferentes.

**Ordem das versões** (decisão de Eduardo, 2026-09-18): `version_date` = **data de publicação** do documento (metadado extraído ou informado na carga); se nula, fallback para a **data de coleta**, marcada como tal na interface; desempate pela ordem de ingestão. "Mais recente" é a versão de maior `version_date`.

**Sugestão de fusão** = estado de ingestão guardado pelo `backend` (F3): par de famílias, score de similaridade, `status: pending | accepted | rejected`, quem e quando decidiu. Gerada ao fim do job de ingestão quando a nova versão não tem chave explícita e passa o limiar contra uma família existente. Confirmada na tela de ingestão/revisão ou pelo atalho no card de resultado, por qualquer usuário autenticado no hackathon, com registro de autoria. Aceitar chama `reassign_family(document_version, family_id)` no serviço vetorial (refinamento do contrato da issue #2, [[i9-integration]]).

## Confirmed facts

- O contrato do serviço vetorial (issue #2) exige `family_id` em todo documento indexado e devolve resultados agrupados por família; deixou para este Topic definir o que é `family_id`.
- Plano, linha 162: versão documental, versão do objeto armazenado e vigência jurídica são atributos distintos; chunk herda a versão documental; documentos mantêm checksum, data de coleta e origem.
- Os tipos documentais concretos do caso 1 (autos, processos SEI, decisões, normas correlatas) e seus metadados ainda dependem da entrega da Carolina (issues #10 e #14).

## Decisions

- 2026-09-18 (issue-3): família = identidade lógica da mesma peça documental; processo SEI = grafo de peças (issue #4), não família.
- 2026-09-18 (issue-3): identificação por chave explícita (tipo + identificador oficial) tem precedência; similaridade só produz sugestão pendente de confirmação, nunca agrupamento automático.
- 2026-09-18 (issue-3): checksum idêntico = mesma versão (não reindexar); vigência é atributo da versão.
- 2026-09-18 (issue-3): `version_date` = data de publicação, fallback data de coleta (marcada); desempate por ordem de ingestão.
- 2026-09-18 (issue-3): sugestão de fusão é estado de ingestão no `backend`, confirmável por qualquer usuário autenticado, com autoria registrada; aceitar aciona `reassign_family` no serviço vetorial.

## Derived requirements and constraints

- Todo documento indexado carrega `family_id`, `document_version` (derivado do checksum do original), `version_date` + `version_date_source` (`publication` | `collection`), ordinal na família e a origem da chave de família (`explicit` | `confirmed-suggestion`).
- Existe uma entidade de **sugestão de agrupamento** (par de famílias, score de similaridade, estado pendente/aceita/rejeitada) separada da família em si; aceitar uma sugestão funde as famílias; rejeitar impede nova sugestão para o mesmo par.
- A regra concreta de extração do identificador oficial por tipo documental é definida quando os documentos do caso 1 chegarem (issue #10); até lá o modelo acima vale e a chave explícita pode ser fornecida manualmente na carga.

## Open questions

- Regras de chave explícita por tipo documental — alimentadas pela issue #10.

## Evidence

- Issue #2, comentário de resolução e `concerns/i9-integration.md` (linha "O que define `family_id` é decisão da issue #3").
- Map issue #1, Notes: "Versões de um mesmo documento são um único objeto na interface; versões similares retornadas pela busca são agrupadas".
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 129, 157, 162, 190.

## Topic history

- issue-3: definiu família/versão/vigência como conceitos distintos, excluiu processo SEI do conceito de família, fixou a precedência chave explícita > similaridade (só sugestão), a ordem das versões por data de publicação e o ciclo da sugestão de fusão.
