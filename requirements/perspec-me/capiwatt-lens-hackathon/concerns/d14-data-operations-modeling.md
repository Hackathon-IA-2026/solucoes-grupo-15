---
concern_id: d14-data-operations-modeling
concern: ~/.claude/skills/perspec-me/catalog/concerns/d14-data-operations-modeling/README.md
perspective: data
status: partial
topics:
  - issue-4 — Como as relações entre documentos são representadas (arestas, origem: metadado explícito vs. similaridade) e onde ficam armazenadas?
updated_at: 2026-09-18
---

## Current resolution

As **relações entre documentos são produzidas no fim do job de ingestão** (mesmo ponto em que a issue #3 gera sugestões de fusão de família), por duas operações distintas sobre os dados (decisão de Eduardo, 2026-09-18):

1. **Extração de referências explícitas** — metadados da fonte (número do processo SEI, órgão) e identificadores reconhecidos no texto extraído (ex.: "Lei nº 11.941, de 2009", "REN 1000/2021", "Auto de Infração nº X"), cada um com o **localizador** (versão + página/artigo/trecho) onde foi encontrado. O identificador é resolvido para um `family_id` pela mesma chave explícita `tipo + identificador oficial` da issue #3 ([[d4-data-dictionary]]). Quando o padrão textual permite classificar a referência ("Revogado pela…", "passa a vigorar com as alterações…", "em resposta ao Auto…"), a aresta recebe o tipo fino (`revoga`, `altera`, `responde_a`, `regula`); caso contrário fica no tipo genérico `referencia`.
2. **Vizinhança vetorial** — para a versão-face de cada família, os k vizinhos mais próximos no índice. Candidatos **acima do limiar de fusão** viram sugestão de fusão (issue #3), **nunca** aresta `similar_a`; candidatos entre o limiar de relação e o de fusão viram aresta `similar_a` **sugerida**, limitada a top-k por família.

**Grafo resultante:** nós = **famílias** de documentos e **processos SEI** (nó de tipo próprio, identificado pelo número SEI — não um documento). Arestas nunca ligam versões; a evidência da aresta é que aponta para `document_version + localizador`.

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

## Decisions

- 2026-09-18 (issue-4): relações são produzidas no fim do job de ingestão por duas operações — extração de referências explícitas e vizinhança vetorial.
- 2026-09-18 (issue-4): nós do grafo = famílias + processos SEI (nó próprio); arestas nunca entre versões; evidência aponta para versão + localizador.
- 2026-09-18 (issue-4): tipos de aresta = `pertence_ao_processo`, `referencia`, `revoga`, `altera`, `responde_a`, `regula`, `similar_a`. Os tipos finos são especialização de uma referência explícita quando o padrão textual permite classificar; senão, `referencia`.
- 2026-09-18 (issue-4): similaridade acima do limiar de fusão → sugestão de fusão (#3), não `similar_a`; nunca contar a mesma vizinhança duas vezes.
- 2026-09-18 (issue-4): referência com alvo fora do corpus é aresta pendente de alvo, preservada.
- 2026-09-18 (issue-4): leitura confirmada por Eduardo — `responde_a` = peça → peça a que responde (defesa → auto de infração; decisão → recurso); `regula` = norma → peça ou processo que ela fundamenta.

## Derived requirements and constraints

- O job de ingestão termina com uma etapa "relações" que emite: lista de referências explícitas `{identificador_bruto, tipo_classificado?, localizador}` e lista de vizinhos `{family_id, score}` por família.
- O reconhecedor de identificadores reutiliza a gramática da chave explícita de família (#3) — uma só definição de "como se escreve o identificador oficial de cada tipo documental".
- Dois limiares distintos e ordenados: `limiar_relacao < limiar_fusao`; documentado junto com o k de vizinhos.
- Toda aresta carrega evidência (`document_version` + localizador) quando `origin: explicit`; `similar_a` carrega o score.

## Open questions

- Instâncias concretas de `regula` e `responde_a` no caso 1 (quais peças do processo de multa respondem a quais; que normas fundamentam o auto) — a leitura provisória está confirmada (abaixo, em Decisions); falta validá-la contra os documentos reais da Carolina. Registrado como comentário na issue #10.
- Valores de `limiar_relacao`, `limiar_fusao` e k — calibrar com os documentos reais e o modelo de embeddings. Registrado como comentário na issue #13.
- Padrões textuais concretos por tipo fino (regex/NER) — definir quando os documentos do caso existirem. Registrado como comentário na issue #10.

## Evidence

- `hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md` linhas 44, 81, 162.
- `ideathon/materiais/inspirations/juridico_wallace/Busca_Legislativa_Inteligente_prototipo.html` — padrões "(Revogado pela Lei nº 11.941, de 2009)", "Art. 22. A Lei nº 14.182 … passa a vigorar com as alterações"; bloco "Normas Relacionadas" (lista plana, sem tipo).
- `concerns/d4-data-dictionary.md`, `concerns/d11-consistency.md` (issue #3).

## Topic history

- issue-4: definiu as duas operações que produzem relações na ingestão, os nós do grafo (família + processo), o vocabulário de tipos de aresta (incluindo os finos `revoga`, `altera`, `responde_a`, `regula`) e a separação entre similaridade-para-fusão e similaridade-para-relação.
