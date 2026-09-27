---
concern_id: d14-data-operations-modeling
concern: ~/.claude/skills/perspec-me/catalog/concerns/d14-data-operations-modeling/README.md
perspective: data
status: partial
topics:
  - issue-4 — Como as relações entre documentos são representadas (arestas, origem: metadado explícito vs. similaridade) e onde ficam armazenadas?
  - issue-92 — Como os candidatos do `ai` (`similar_families`, `references[]`) viram arestas, respeitando os limiares calibrados na #74?
  - issue-13 — Que estratégia de chunking e que modelo de embeddings do Bedrock se ajustam aos documentos do caso 1?
updated_at: 2026-09-27
---

## Current resolution

As **relações entre documentos são produzidas no fim do job de ingestão** (mesmo ponto em que a issue #3 gera sugestões de fusão de família), por duas operações distintas sobre os dados (decisão de Eduardo, 2026-09-18):

1. **Extração de referências explícitas** — metadados da fonte (número do processo SEI, órgão) e identificadores reconhecidos no texto extraído (ex.: "Lei nº 11.941, de 2009", "REN 1000/2021", "Auto de Infração nº X"), cada um com o **localizador** (versão + página/artigo/trecho) onde foi encontrado. O identificador é resolvido para um `family_id` pela mesma chave explícita `tipo + identificador oficial` da issue #3 ([[d4-data-dictionary]]). Quando o padrão textual permite classificar a referência ("Revogado pela…", "passa a vigorar com as alterações…", "em resposta ao Auto…"), a aresta recebe o tipo fino (`revoga`, `altera`, `responde_a`, `regula`); caso contrário fica no tipo genérico `referencia`.
2. **Vizinhança vetorial** — para a versão-face de cada família, os k vizinhos mais próximos no índice. Candidatos **acima do limiar de fusão** viram sugestão de fusão (issue #3), **nunca** aresta `similar_a`; candidatos entre o limiar de relação e o de fusão viram aresta `similar_a` **sugerida**, limitada a top-k por família.

**Grafo resultante:** nós = **famílias** de documentos e **processos SEI** (nó de tipo próprio, identificado pelo número SEI — não um documento). Arestas nunca ligam versões; a evidência da aresta é que aponta para `document_version + localizador`.

**Etapa de extração por IA, antes do chunking (decisão de Eduardo, 2026-09-26)**: todo PDF, de qualquer um dos dois corpora (`case-1-carolina-mmgd/` e o corpus maior da #56), passa por uma IA que extrai o texto para um arquivo Markdown — menor e mais fácil de tratar do que o PDF original. Essa IA **copia o conteúdo**, nunca resume com palavras próprias, e remove: (1) anexos inteiros como relatório de vistoria e laudo técnico, (2) contrato social, e (3) assinaturas e a identificação de quem assinou. O chunking estrutural abaixo passa a rodar sobre o Markdown extraído, não sobre o texto bruto do PDF.

Para a representação vetorial decidida na issue #13, cada versão documental passa por **chunking estrutural** com alvo de 600 tokens, máximo de 800 e sobreposição de 100 tokens apenas entre trechos narrativos adjacentes. Títulos, seções, parágrafos e tabelas orientam os limites; cabeçalhos e rodapés repetidos são removidos. Cada chunk preserva `document_id`, `corpus_version`, `model_version`, versão documental, seção e intervalo de páginas.

Depois de recuperar os três chunks mais relevantes, a variante *small-to-big* amplia cada resultado para todo o texto das páginas atingidas pelo chunk, mais a página anterior e a seguinte. Intervalos sobrepostos são unidos, a duplicação introduzida pela sobreposição dos chunks é eliminada e a ordem original das páginas é preservada. A expansão nunca atravessa a versão documental. Um orçamento explícito de contexto prioriza resultados melhor classificados e registra páginas omitidas, sem truncar páginas silenciosamente.

**Vocabulário de tipos de aresta** (decisão de Eduardo, 2026-09-18):

| Tipo | De → Para | Origem típica |
|---|---|---|
| `pertence_ao_processo` | peça → processo | metadado explícito (SEI) |
| `referencia` | família → família | identificador no texto, sem classificação fina |
| `revoga` | norma → norma | padrão textual explícito |
| `altera` | norma → norma | padrão textual explícito |
| `responde_a` | peça → peça (defesa → auto de infração; decisão → recurso) | padrão textual / metadado do processo |
| `regula` | norma → peça ou processo (a norma que fundamenta o ato) | padrão textual explícito ("com fundamento na…", "nos termos da…") |
| `similar_a` | família ↔ família | vizinhança vetorial (só sugestão) |

Referências cujo alvo **não está no corpus** ficam como aresta **pendente de alvo**, guardando o identificador citado — insumo da futura detecção de baixa cobertura, não descarte.

**Implementação da etapa "relações" (issue-92, 2026-09-27).** O fim do job de ingestão do `backend` (`app/ai_relations.py`) consome os candidatos do `ai` assim:

- **Vizinhança:** para cada família do corpus ingerido, pede `similar_families(family_id, top_k=3)`. Quando `limiar_relacao (0.80) <= score < limiar_fusao (0.97)`, grava uma aresta `similar_a` com `origin: similarity`, `status: suggested` e `score`. A vizinhança é simétrica, então cada par é gravado uma única vez, com as pontas em ordem lexicográfica. Quando `score >= limiar_fusao`, o candidato é de fusão e nunca vira `similar_a`. Como o backend ainda não tem a máquina de sugestão de fusão (#22), esse candidato é descartado. Abaixo de `limiar_relacao`, o candidato também é descartado. Vizinho fora do catálogo é ignorado. Numa reingestão, só o `score` é atualizado; o `status` de uma aresta existente é preservado.
- **Referências:** cada `identifier_raw` de auto de infração é resolvido pela chave `(número, ano, sigla?)` contra o `document_id` das versões do catálogo (ex.: "AI 0017/2020-SFE"). A sigla precisa bater quando os dois lados a têm. Quando a resolução dá um único alvo diferente da própria família, grava uma aresta `referencia` (ou o `relation_type` fino enviado) com `origin: explicit`, `status: confirmed` e evidência `(document_version, chunk_id)` da primeira ocorrência.
- No caso 1 real (e2e), isso produz exatamente os 11 pares `similar_a` da calibração da #74, com os mesmos scores, e 7 arestas `referencia` recurso/voto/complementação → auto de infração.

## Confirmed facts

- Plano (linha 44): F2 implementa "relações documentais"; (linha 81): "relações mínimas começam como metadados com evidência", Neptune é evolução.
- Protótipos de UI (`juridico_referencia/`) contêm padrões textuais "(Revogado pela Lei nº …)" e "passa a vigorar com as alterações…" — referências explícitas extraíveis por identificador.
- Issue #3: processo SEI não é família; peças distintas ligadas por aresta; chave explícita `tipo + identificador oficial` já existe e serve para resolver alvos de referência.
- O corpus real da Carolina contém 10 PDFs com 5 a 71 páginas e texto extraível por página; a estrutura inclui seções numeradas, tabelas e cabeçalhos/rodapés repetidos.
- O adapter atual de `hackathon/ai/app/routes/index.py` apenas conta blocos separados por linhas em branco em fixtures e declara que isso não é uma estratégia real de chunking.

## Decisions

- 2026-09-18 (issue-4): relações são produzidas no fim do job de ingestão por duas operações — extração de referências explícitas e vizinhança vetorial.
- 2026-09-18 (issue-4): nós do grafo = famílias + processos SEI (nó próprio); arestas nunca entre versões; evidência aponta para versão + localizador.
- 2026-09-18 (issue-4): tipos de aresta = `pertence_ao_processo`, `referencia`, `revoga`, `altera`, `responde_a`, `regula`, `similar_a`. Os tipos finos são especialização de uma referência explícita quando o padrão textual permite classificar; senão, `referencia`.
- 2026-09-18 (issue-4): similaridade acima do limiar de fusão → sugestão de fusão (#3), não `similar_a`; nunca contar a mesma vizinhança duas vezes.
- 2026-09-18 (issue-4): referência com alvo fora do corpus é aresta pendente de alvo, preservada.
- 2026-09-18 (issue-4): leitura confirmada por Eduardo — `responde_a` = peça → peça a que responde (defesa → auto de infração; decisão → recurso); `regula` = norma → peça ou processo que ela fundamenta.
- 2026-09-22 (issue-13, Eduardo): chunking estrutural com alvo de 600 tokens, máximo de 800 e sobreposição narrativa de 100 tokens; chunks não atravessam versões documentais.
- 2026-09-22 (issue-13, Eduardo): recuperação *small-to-big* orientada a páginas depois dos três chunks encontrados; o intervalo do chunk é ampliado com a página anterior e a seguinte.
- 2026-09-22 (issue-13, Eduardo): `Recall@3` é calculado sobre os chunks encontrados antes da expansão; a qualidade da resposta e das citações após expansão é avaliada separadamente.
- 2026-09-22 (issue-13, Eduardo): `top_k=3` para candidatos de vizinhança; `limiar_relacao` e `limiar_fusao` são calibrados no corpus, sem constantes universais, mantendo `limiar_relacao < limiar_fusao`.
- 2026-09-27 (issue-92, agente): `limiar_relacao = 0.80`, `limiar_fusao = 0.97` e `top_k = 3` passam a ser lidos pelo código de produção (`backend/app/ai_relations.py`). O vetor de família do `ai` (`ai/app/family_similarity.py`) usa a mesma agregação (média renormalizada de todos os chunks da família) sobre a qual os limiares foram calibrados.
- 2026-09-26 (issue-13, Eduardo): inserir uma etapa de extração por IA (PDF → Markdown, cópia verbatim, sem resumo) antes do chunking estrutural; aplicada a todo documento de ambos os corpora.
- 2026-09-26 (issue-13, Eduardo): essa extração remove anexos inteiros (relatório de vistoria, laudo técnico), contrato social, e assinaturas/identificação de quem assinou — não apenas boilerplate de assinatura.
- 2026-09-26 (issue-13, Eduardo): o corpus maior da #56 não substitui o gabarito de avaliação de D16 (que continua nos 10 PDFs de `case-1-carolina-mmgd/`); ele serve para popular o dataset, dar robustez às métricas de busca e como fonte de futuros casos de teste.
- 2026-09-26 (issue-61): `limiar_relacao = 0.80` e `limiar_fusao = 0.97` (produto interno / cosseno, mesma métrica de #60), calibrados contra a vizinhança vetorial real das 10 famílias do corpus (`top_k=3` fixado). Evidência completa em `hackathon/tools/prototypes/family_similarity/` (matriz de 45 pares, `output/family_similarity.json`, `output/calibration_report.json`). O par positivo conhecido (recurso `48500.009907-2025-96` ↔ complementação `48500.017555-2025-42`, referência textual explícita confirmada) cai em `similar_a` (score 0,8062). Nenhum par entre famílias distintas cruza `limiar_fusao` (teto observado 0,9278, margem de 0,042) — consistente com a lacuna já registrada abaixo (não há par de fusão real neste corpus). Achado documentado no protótipo: a hipótese de "par de controle sem relação" (dois autos de infração de casos não relacionados) não se confirmou como piso de similaridade — ficou em 0,8368, acima do par positivo conhecido — por gabarito administrativo rígido dos autos de infração; `limiar_relacao` foi calibrado priorizando não perder o par positivo mandatado pela issue, aceitando esse par como ruído conhecido na faixa `similar_a` (aresta apenas sugerida, nunca fusão automática).
- 2026-09-26 (issue-74): `limiar_relacao = 0.80` e `limiar_fusao = 0.97` **reconfirmados sem alteração**, agora recalibrados contra os embeddings REAIS persistidos pelo serviço `ai` ao indexar o corpus (issue #73, `RawVectorStore`), não mais contra os embeddings do protótipo isolado da #60/#61. Evidência em `hackathon/tools/case1_recall/similarity_calibration/` (`output/family_similarity.json`, `output/calibration_report.json`, `output/aggregation_alternative_report.json`). Os 45 pares reproduzem, valor a valor, os scores da #61 (par positivo 0,8062, par de controle 0,8368, teto 0,9278, contagem 34/11/0) — esperado, já que o chunker de produção (`ai/app/chunking.py`) é uma port quase verbatim do protótipo sobre o mesmo texto extraído; a recalibração vale por repousar na cadeia real de produção, não por ter mudado a amostra. Distribuição de similaridade por bucket reportada pela primeira vez: `mesmo_processo` (n=12, mediana 0,8696), `mesmo_tema`/processo diferente (n=7, mediana 0,7051, teto 0,8368 = o próprio par de controle), `temas_diferentes` (n=26, mediana 0,6868). Confiança explicitamente marcada como menor do que uma calibração contra corpus maior (mesma amostra de 10 documentos da #61, nenhum par de fusão real disponível). Estratégia de vetor de agregação reavaliada: a alternativa "só o trecho de motivação/fundamentação" foi descartada porque não é computável para o próprio par positivo mandatado pela issue (só 3 das 10 famílias têm chunk de "motivação" sob a heurística de heading atual) — mean-of-all-chunks mantido.

## Derived requirements and constraints

- O job de ingestão termina com uma etapa "relações" que emite: lista de referências explícitas `{identificador_bruto, tipo_classificado?, localizador}` e lista de vizinhos `{family_id, score}` por família.
- O reconhecedor de identificadores reutiliza a gramática da chave explícita de família (#3) — uma só definição de "como se escreve o identificador oficial de cada tipo documental".
- Dois limiares distintos e ordenados: `limiar_relacao < limiar_fusao`; documentado junto com o k de vizinhos.
- Toda aresta carrega evidência (`document_version` + localizador) quando `origin: explicit`; `similar_a` carrega o score.
- O parser deve remover cabeçalhos e rodapés repetidos, preservar a estrutura de seções e manter tabelas inteiras quando couberem; ao dividir uma tabela, repete seu cabeçalho.
- Cada chunk carrega `document_id`, `corpus_version`, `model_version`, versão documental, seção e páginas inicial/final, além do vínculo necessário para reconstruir o texto original das páginas.
- A expansão usa o intervalo completo quando um chunk atravessa páginas, soma uma página anterior e uma posterior dentro da mesma versão e une intervalos sobrepostos antes de montar o contexto.
- A montagem de contexto elimina texto duplicado pela sobreposição dos chunks, preserva a ordem das páginas e cita as páginas que efetivamente sustentam a resposta, inclusive quando vizinhas à página que originou o hit.
- O orçamento de contexto é explícito e determinístico: prioriza hits pela classificação original, inclui apenas páginas inteiras e registra toda página omitida.
- Resultados pré-expansão e pós-expansão são persistidos separadamente para permitir comparar recuperação, qualidade da resposta e correção das citações.
- Se o baseline falhar no gate de `Recall@3 >= 2/3`, o mesmo experimento compara chunks de aproximadamente 400 e 800 tokens, mantendo as demais variáveis fixas.

## Open questions

- Instâncias concretas de `regula` e `responde_a` no caso 1 (quais peças do processo de multa respondem a quais; que normas fundamentam o auto) — a leitura provisória está confirmada (abaixo, em Decisions); falta validá-la contra os documentos reais da Carolina. Registrado como comentário na issue #10.
- **Resolvida em 2026-09-26 (issue-61), reconfirmada em 2026-09-26 (issue-74)**: `limiar_relacao = 0.80`, `limiar_fusao = 0.97` (`top_k=3` mantido); evidência em `hackathon/tools/prototypes/family_similarity/` (embeddings do protótipo, #61) e `hackathon/tools/case1_recall/similarity_calibration/` (embeddings reais persistidos pela #73, #74 — mesmos números, ver Decisions). O corpus atual não contém nenhum par de fusão real (nenhuma família duplicada/retificada) — `limiar_fusao` foi calibrado de forma defensável (acima do teto observado entre famílias distintas, com margem justificada), não contra um positivo real; revisitar quando um caso real de republicação/retificação aparecer nos dados (ainda não aparece após a #73 — mesma amostra de 10 documentos).
- Padrões textuais concretos por tipo fino (regex/NER) — definir quando os documentos do caso existirem. Registrado como comentário na issue #10.
- **Resolvida em 2026-09-26**: a extração remove seções inteiras de anexo (vistoria, laudo técnico), contrato social e assinaturas (ver Decisions).
- Como distinguir programaticamente "anexo" de "conteúdo principal" dentro do Markdown extraído (heurística por título de seção, classificação por página, ou decisão da própria IA de extração durante a cópia) não foi especificado — a decisão de 2026-09-26 fixa o quê remover, não o como a IA identifica os limites de cada seção.

- (issue-92, aberta — decisão conservadora do agente, pendente de Eduardo) Referência com alvo fora do corpus ou ambíguo **não é gravada** por ora, porque a "aresta pendente de alvo" decidida na issue-4 ainda não tem representação no schema (`target_external_ref`, novo `target_kind`) nem na interface. Falta decidir essa representação.
- (issue-92, aberta) Candidato com `score >= limiar_fusao` é só descartado, porque não existe tabela de sugestão de fusão (#22). No caso 1 isso não acontece (teto 0,9278).
- (issue-92, aberta) O reconhecedor de referências só cobre auto de infração ("Auto de Infração [– AI –] nº N/AAAA[-SIGLA]"); leis, REN, número SEI e tipos finos (`revoga`/`altera`/`responde_a`/`regula`) continuam sem padrão definido. Número SEI citado resolveria para um nó `processo`, e o vocabulário não tem tipo de aresta família → processo além de `pertence_ao_processo`.
- (issue-92, aberta) d14 fala em vizinhança "da versão-face de cada família". O `ai` não conhece datas de versão e agrega todos os chunks da família, como a calibração da #74 fez. No caso 1 isso é equivalente, porque cada família tem uma versão só; para famílias com várias versões, é preciso decidir.
- (issue-92, aberta) Arestas `similar_a` que deixam de se qualificar numa reingestão (ex.: troca de modelo) não são removidas.

## Evidence

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 44, 81, 162.
- `ideathon/materiais/inspirations/juridico_referencia/Busca_Legislativa_Inteligente_prototipo.html` — padrões "(Revogado pela Lei nº 11.941, de 2009)", "Art. 22. A Lei nº 14.182 … passa a vigorar com as alterações"; bloco "Normas Relacionadas" (lista plana, sem tipo).
- `concerns/d4-data-dictionary.md`, `concerns/d11-consistency.md` (issue #3).
- `hackathon/data/case-1-carolina-mmgd/` — corpus real de 10 PDFs usado para caracterizar páginas e estrutura documental.
- `hackathon/ai/app/routes/index.py` — comportamento provisório de fixtures que será substituído pelo chunking estrutural.
- Resposta de Eduardo na sessão da issue #13, 2026-09-22 — baseline de chunking, expansão por páginas, orçamento de contexto, métricas separadas e calibração de vizinhança.
- Resposta de Eduardo na sessão da issue #13, 2026-09-26 — etapa de extração por IA (PDF → Markdown, cópia verbatim, remoção de assinaturas), aplicada a ambos os corpora; papel do corpus maior da #56 (popular dataset, robustez de métricas, futuros casos de teste).
- `hackathon/tools/prototypes/family_similarity/` (issue #61, 2026-09-26) — vetor por família (média renormalizada dos embeddings de chunk de #60), matriz de similaridade completa (45 pares) e top-3 vizinhos das 10 famílias reais, calibração de `limiar_relacao`/`limiar_fusao` contra os pares conhecidos do corpus, com o achado de que o par de controle hipotetizado não serviu de piso negativo confiável.
- `hackathon/tools/case1_recall/similarity_calibration/` (issue #74, 2026-09-26) — mesma calibração, agora contra os vetores REAIS persistidos pelo serviço `ai` (issue #73, `RawVectorStore`): mesma matriz de 45 pares (scores idênticos aos da #61), distribuição de similaridade por bucket `mesmo_processo`/`mesmo_tema`/`temas_diferentes`, e avaliação registrada da alternativa de vetor de agregação "só motivação" (descartada — não computável para o par positivo conhecido).

## Topic history

- issue-92 (2026-09-27): ligou a etapa "relações" ao código — `similar_families`/`references[]` no `ai`, e limiares da #74 aplicados pelo `backend` ao gravar `similar_a` e `referencia` em `document_relations`; registrou as lacunas (alvo pendente, fusão, tipos finos, versão-face) como questões abertas.

- issue-4: definiu as duas operações que produzem relações na ingestão, os nós do grafo (família + processo), o vocabulário de tipos de aresta (incluindo os finos `revoga`, `altera`, `responde_a`, `regula`) e a separação entre similaridade-para-fusão e similaridade-para-relação.
- issue-13: definiu o chunking estrutural, a expansão *small-to-big* por páginas, a proveniência e o orçamento do contexto, separou as métricas pré/pós-expansão e fixou `top_k=3`; os limiares numéricos permanecem para calibração no corpus.
- issue-13 (2026-09-26): travou o modelo em Titan V2, adiou a medição de `Recall@3`, fechou a #56 e inseriu uma etapa de extração por IA (PDF → Markdown, cópia verbatim) antes do chunking, aplicada a ambos os corpora, removendo anexos inteiros (vistoria, laudo técnico), contrato social e assinaturas; abriu a #57 (D1/U4) para o link do documento na interface.
- issue-61 (2026-09-26): calibrou `limiar_relacao = 0.80` e `limiar_fusao = 0.97` contra a vizinhança vetorial real das 10 famílias do corpus; documentou que o corpus não tem par de fusão real disponível e que o par de controle hipotetizado (mesmo tipo documental, casos não relacionados) não serviu de piso negativo confiável nesta calibração.
- issue-74 (2026-09-26): reconfirmou os mesmos limiares contra os embeddings reais persistidos pela #73 (mesmos scores da #61); acrescentou a distribuição de similaridade por bucket (mesmo processo / mesmo tema / temas diferentes) e registrou a decisão de manter mean-of-all-chunks como vetor de agregação, descartando a alternativa "só motivação" por não ser computável para o par positivo conhecido.
