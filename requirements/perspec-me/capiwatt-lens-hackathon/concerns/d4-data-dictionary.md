---
concern_id: d4-data-dictionary
concern: ~/.claude/skills/perspec-me/catalog/concerns/d4-data-dictionary/README.md
perspective: data
status: partial
topics:
  - issue-3 — Como uma família de versões de um documento é identificada e agrupada num único objeto, na ingestão e no resultado da busca?
  - issue-10 — Quais tipos de documento compõem o caso 1 e quais metadados cada um precisa carregar?
updated_at: 2026-09-22
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

**Tipos concretos do corpus do caso 1**: `auto_de_infracao`, `exposicao_de_motivos`, `recurso_administrativo`, `complementacao_de_recurso` e `voto`. `nota_tecnica` e `juizo_de_reconsideracao` pertencem ao vocabulário do caso, mas não estão presentes na entrega atual. Processo administrativo continua sendo nó agregador, não `document_type` nem família. Norma citada é uma entidade de referência ligada por `regula` e não é indexada no primeiro ciclo.

**Metadados comuns por versão**: tipo e subtipo; título/assunto; identificador oficial da peça; NUP próprio da peça; processo administrativo principal e aliases; agente/interessado e CNPJ quando disponível; órgão/unidade emissora; autor, signatário ou relator; datas do documento, publicação e coleta com a origem de cada data; sistema e localizador oficiais; canal de aquisição; classificação de acesso declarada e encontrada; checksum, páginas e estado da extração de texto; `family_id`, `document_version`, `version_date`, vigência e estado de aplicabilidade.

**Metadados específicos**:

- Auto/exposição: número do auto, termo de notificação e relatório de fiscalização relacionados, infrações/não conformidades, dispositivos descumpridos, enquadramento, penalidade inicial, valor inicial, prazo recursal e autoridade autuante.
- Recurso/complementação: número da carta ou peça, auto recorrido, recorrente, data de protocolo, pedidos, argumentos/fundamentos e normas citadas; complementação aponta também para o recurso que complementa.
- Voto: reunião/item e data, processo, interessado, relator, unidade responsável, recurso e auto julgados, conclusão/provimento, penalidades mantidas/anuladas/reduzidas, valor inicial/final e fundamentos/normas citadas.
- Referência normativa: espécie, número, ano, órgão emissor e dispositivo citado, sempre com trecho de evidência e página de origem.

**Chave explícita por tipo**: `document_type + official_document_id + issuing_unit` quando a peça possui identificador próprio; para peças sem número inequívoco, usar `document_type + process_number_normalized + document_date + author_or_issuer`, mantendo a chave como provisória até revisão humana. NUP identifica processo ou protocolo, não substitui automaticamente o identificador da peça.

## Confirmed facts

- O contrato do serviço vetorial (issue #2) exige `family_id` em todo documento indexado e devolve resultados agrupados por família; deixou para este Topic definir o que é `family_id`.
- Plano, linha 162: versão documental, versão do objeto armazenado e vigência jurídica são atributos distintos; chunk herda a versão documental; documentos mantêm checksum, data de coleta e origem.
- A entrega da Carolina está em `hackathon/data/case-1-carolina-mmgd/` e contém 10 PDFs: 3 autos/exposições, 3 recursos, 1 complementação e 3 votos.
- O corpus confirma que uma peça pode ter NUP próprio diferente do processo administrativo a que pertence; o caso Coelba relaciona `48500.001433/2024-53`, `48500.901433/2024-53`, `48500.009907/2025-96` e `48500.017555/2025-42`.
- Os cabeçalhos e corpos dos documentos trazem referências explícitas suficientes para materializar `responde_a` entre recurso e auto, complementação e recurso, e voto e recurso; normas citadas materializam `regula` com evidência textual.
- Ocorrências lexicais de “revogar” ou “alterar” em argumentos jurídicos e fórmulas de competência não provam uma aresta `revoga` ou `altera` entre documentos.

## Decisions

- 2026-09-18 (issue-3): família = identidade lógica da mesma peça documental; processo SEI = grafo de peças (issue #4), não família.
- 2026-09-18 (issue-3): identificação por chave explícita (tipo + identificador oficial) tem precedência; similaridade só produz sugestão pendente de confirmação, nunca agrupamento automático.
- 2026-09-18 (issue-3): checksum idêntico = mesma versão (não reindexar); vigência é atributo da versão.
- 2026-09-18 (issue-3): `version_date` = data de publicação, fallback data de coleta (marcada); desempate por ordem de ingestão.
- 2026-09-18 (issue-3): sugestão de fusão é estado de ingestão no `backend`, confirmável por qualquer usuário autenticado, com autoria registrada; aceitar aciona `reassign_family` no serviço vetorial.
- 2026-09-22 (issue-10): o dicionário distingue tipo documental, identificador oficial da peça, NUP próprio e processo administrativo principal; nenhum desses campos substitui automaticamente os demais.
- 2026-09-22 (issue-10): processo administrativo permanece nó agregador, e norma apenas citada permanece entidade de referência enquanto não houver texto normativo entregue como documento.
- 2026-09-22 (issue-10): normas não serão indexadas no primeiro ciclo, mesmo quando citadas; somente sua identidade, dispositivo e evidência da citação entram no dicionário e no grafo.
- 2026-09-22 (issue-10): a origem dos arquivos entregues é `sei_aneel`; a cópia do recurso CEMIG está autorizada para exposição, preservando `Reservada` como marca histórica separada da autorização atual.

## Derived requirements and constraints

- Todo documento indexado carrega `family_id`, `document_version` (derivado do checksum do original), `version_date` + `version_date_source` (`publication` | `collection`), ordinal na família e a origem da chave de família (`explicit` | `confirmed-suggestion`).
- Existe uma entidade de **sugestão de agrupamento** (par de famílias, score de similaridade, estado pendente/aceita/rejeitada) separada da família em si; aceitar uma sugestão funde as famílias; rejeitar impede nova sugestão para o mesmo par.
- A issue #10 refinou a extração do identificador oficial por tipo documental; quando a peça não trouxer identificador inequívoco, a carga mantém uma chave provisória e permite fornecimento ou revisão manual.
- A regra concreta de extração usa rótulos contextuais (`AI nº`, `Auto de Infração nº`, `Carta`, `Voto`, `PROCESSO`, `Processo Administrativo`, `SEI`) e valida o identificador contra o tipo e a unidade emissora; regex encontra candidatos, mas a associação contextual precisa de regras/NER e evidência de página.
- `responde_a` exige expressão relacional explícita como “recurso ... em face do Auto de Infração nº ...”, “complementar o recurso” ou voto cujo assunto identifique o recurso julgado; mera coocorrência no mesmo processo não basta.
- `regula` exige citação identificável de norma/dispositivo no contexto de fundamento, infração, enquadramento ou decisão, guardando trecho e página.
- `revoga` e `altera` só podem nascer `confirmed` quando o texto contém ato performativo e alvo documental inequívoco; usos hipotéticos, citações de competência ou alterações fáticas não geram aresta.

## Open questions

- Confirmar a política para peças sem identificador próprio inequívoco: manter chave provisória até revisão humana ou aceitar a composição processo + data + autor/unidade como chave definitiva.

## Evidence

- Issue #2, comentário de resolução e `concerns/i9-integration.md` (linha "O que define `family_id` é decisão da issue #3").
- Map issue #1, Notes: "Versões de um mesmo documento são um único objeto na interface; versões similares retornadas pela busca são agrupadas".
- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 129, 157, 162, 190.
- `hackathon/data/case-1-carolina-mmgd/README.md` e os 10 PDFs inventariados — tipos concretos, identificadores, relações explícitas e campos específicos.

## Topic history

- issue-3: definiu família/versão/vigência como conceitos distintos, excluiu processo SEI do conceito de família, fixou a precedência chave explícita > similaridade (só sugestão), a ordem das versões por data de publicação e o ciclo da sugestão de fusão.
- issue-10: acrescentou a taxonomia concreta do caso 1, metadados comuns e específicos, chaves por tipo e critérios conservadores para extrair `responde_a`, `regula`, `revoga` e `altera`; confirmou SEI/ANEEL como origem, a exposição autorizada da cópia CEMIG e a não indexação das normas.
