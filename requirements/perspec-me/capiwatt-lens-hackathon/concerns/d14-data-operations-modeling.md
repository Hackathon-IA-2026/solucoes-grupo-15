---
concern_id: d14-data-operations-modeling
concern: ~/.claude/skills/perspec-me/catalog/concerns/d14-data-operations-modeling/README.md
perspective: data
status: partial
topics:
  - issue-4 — Como as relações entre documentos são representadas (arestas, origem: metadado explícito vs. similaridade) e onde ficam armazenadas?
  - issue-13 — Que estratégia de chunking e que modelo de embeddings do Bedrock se ajustam aos documentos do caso 1?
updated_at: 2026-09-22
---

## Current resolution

As **relações entre documentos são produzidas no fim do job de ingestão** (mesmo ponto em que a issue #3 gera sugestões de fusão de família), por duas operações distintas sobre os dados (decisão de Eduardo, 2026-09-18):

1. **Extração de referências explícitas** — metadados da fonte (número do processo SEI, órgão) e identificadores reconhecidos no texto extraído (ex.: "Lei nº 11.941, de 2009", "REN 1000/2021", "Auto de Infração nº X"), cada um com o **localizador** (versão + página/artigo/trecho) onde foi encontrado. O identificador é resolvido para um `family_id` pela mesma chave explícita `tipo + identificador oficial` da issue #3 ([[d4-data-dictionary]]). Quando o padrão textual permite classificar a referência ("Revogado pela…", "passa a vigorar com as alterações…", "em resposta ao Auto…"), a aresta recebe o tipo fino (`revoga`, `altera`, `responde_a`, `regula`); caso contrário fica no tipo genérico `referencia`.
2. **Vizinhança vetorial** — para a versão-face de cada família, os k vizinhos mais próximos no índice. Candidatos **acima do limiar de fusão** viram sugestão de fusão (issue #3), **nunca** aresta `similar_a`; candidatos entre o limiar de relação e o de fusão viram aresta `similar_a` **sugerida**, limitada a top-k por família.

**Grafo resultante:** nós = **famílias** de documentos e **processos SEI** (nó de tipo próprio, identificado pelo número SEI — não um documento). Arestas nunca ligam versões; a evidência da aresta é que aponta para `document_version + localizador`.

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

## Confirmed facts

- Plano (linha 44): F2 implementa "relações documentais"; (linha 81): "relações mínimas começam como metadados com evidência", Neptune é evolução.
- Protótipos de UI (`juridico_wallace/`) contêm padrões textuais "(Revogado pela Lei nº …)" e "passa a vigorar com as alterações…" — referências explícitas extraíveis por identificador.
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
- Valores numéricos de `limiar_relacao` e `limiar_fusao` — calibrar com pares conhecidos do corpus após a invocação funcional do modelo; `top_k` foi fixado em 3 e a ordenação `limiar_relacao < limiar_fusao` permanece obrigatória.
- Padrões textuais concretos por tipo fino (regex/NER) — definir quando os documentos do caso existirem. Registrado como comentário na issue #10.

## Evidence

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 44, 81, 162.
- `ideathon/materiais/inspirations/juridico_wallace/Busca_Legislativa_Inteligente_prototipo.html` — padrões "(Revogado pela Lei nº 11.941, de 2009)", "Art. 22. A Lei nº 14.182 … passa a vigorar com as alterações"; bloco "Normas Relacionadas" (lista plana, sem tipo).
- `concerns/d4-data-dictionary.md`, `concerns/d11-consistency.md` (issue #3).
- `hackathon/data/case-1-carolina-mmgd/` — corpus real de 10 PDFs usado para caracterizar páginas e estrutura documental.
- `hackathon/ai/app/routes/index.py` — comportamento provisório de fixtures que será substituído pelo chunking estrutural.
- Resposta de Eduardo na sessão da issue #13, 2026-09-22 — baseline de chunking, expansão por páginas, orçamento de contexto, métricas separadas e calibração de vizinhança.

## Topic history

- issue-4: definiu as duas operações que produzem relações na ingestão, os nós do grafo (família + processo), o vocabulário de tipos de aresta (incluindo os finos `revoga`, `altera`, `responde_a`, `regula`) e a separação entre similaridade-para-fusão e similaridade-para-relação.
- issue-13: definiu o chunking estrutural, a expansão *small-to-big* por páginas, a proveniência e o orçamento do contexto, separou as métricas pré/pós-expansão e fixou `top_k=3`; os limiares numéricos permanecem para calibração no corpus.
