---
concern_id: u4-visualization
concern: ~/.claude/skills/perspec-me/catalog/concerns/u4-visualization/README.md
perspective: user-experience
status: partial
topics:
  - issue-3 — Como uma família de versões de um documento é identificada e agrupada num único objeto, na ingestão e no resultado da busca?
  - issue-5 — Como a interface expõe a exploração do grafo de relações e o objeto-documento com versões, a partir dos protótipos juridico_wallace?
  - issue-28 — Como a busca pagina resultados ordenados por relevância em lotes de 10 sem alterar a ordem entre páginas?
updated_at: 2026-09-25
---

## Current resolution

No resultado da busca, **um card por família**. A "face" do card é **a versão mais recente da família** (decisão de Eduardo, 2026-09-18 — "certamente"), não a versão de melhor correspondência. O trecho que casou com a consulta é exibido com a **etiqueta da versão em que ocorreu** (ex.: "trecho na versão de 12/03/2024 — superada"), para que a evidência recuperada numa versão antiga não se perca nem seja confundida com o texto atual. O card expõe a lista/linha do tempo de versões da família.

Isto refina o contrato da issue #2, que descrevia o hit como "versão de melhor correspondência + chunks": a `SearchResult` passa a carregar, por família, a versão mais recente (face) **e** os chunks que casaram, cada um com sua `document_version`. O agrupamento continua sendo obrigação do serviço vetorial (issue #2); a apresentação é da F1.

**Carregamento lazy do resultado (issue-28, Eduardo, 2026-09-25).** A lista de resultados mostra **10 famílias por vez** e carrega as próximas 10 sob demanda. Os lotes são **acrescentados** ao fim da lista; nenhum card já exibido muda de posição quando o lote seguinte chega. A ordenação global é congelada na primeira chamada ([[i9-integration]]).

A contagem exibida é o **total do conjunto congelado**, não o número de cards já carregados. Hoje a tela deriva o rótulo de `results.length` (`hackathon/frontend/src/pages/SearchPage.tsx:121`), o que passaria a mentir assim que a lista fosse parcial: diria "10 famílias encontradas" havendo 34. O envelope carrega `total`, e é ele que o rótulo usa.

O gatilho de "carregar mais" precisa ser alcançável por teclado. Rolagem infinita sozinha esconde o rodapé e deixa o usuário sem alcançar o fim da página.

Quando existir `corpus_version` mais recente que a do conjunto congelado, a interface avisa e oferece **refazer a busca**. Ela não injeta resultados novos na lista aberta — misturar corpora quebraria a ordem estável e o vínculo com `corpus_version` que a evidência precisa ter.

Uma **sugestão de fusão pendente aparece na busca** (decisão de Eduardo, 2026-09-18): os dois cards continuam separados e cada um traz um aviso discreto "possível versão de <outra família>" com atalho para confirmar ou rejeitar. Quando `version_date` vem da data de coleta (sem data de publicação), o card marca a data como "coleta".

**Objeto-documento e grafo (issue #5, decisão de Eduardo, 2026-09-18).** A página de uma família tem três blocos. Cabeçalho da família: tipo, identificador oficial, processo SEI a que pertence (link para a página do processo), data e origem da data (publicação ou coleta). Linha do tempo de versões, com a mais recente selecionada e as demais clicáveis; o corpo mostra o texto da versão selecionada, com os trechos que casaram com a busca destacados no padrão "Trecho relevante" do protótipo e etiquetados pela versão em que ocorreram. Painel "Relações": grafo egocêntrico de um salto, no formato estrela que o protótipo esboçou na tela `network` e nunca ligou, com a família no centro e os vizinhos agrupados por tipo de aresta; clicar num vizinho recentra o grafo nele.

Não existe tela de grafo global no TB1. A exploração parte sempre de uma família ou de um processo SEI. O processo SEI, nó próprio pelo #4, ganha página própria: lista das peças ordenadas por data, com a cadeia `responde_a` visível, e o mesmo painel "Relações".

O histórico por artigo inline do protótipo ("Redação dada pela Lei nº ...", com redações antigas empilhadas) fica de fora. O modelo é versão do documento inteiro (#3); diff entre versões não entra no TB1.

Confirmar uma aresta `similar_a` sugerida, ou uma sugestão de fusão de família (#3), acontece inline na página do documento, não numa fila de revisão separada. A ação registra quem confirmou.

## Confirmed facts

- Reunião de 2026-09-17: versões de um mesmo documento são um único objeto na interface; versões similares retornadas pela busca são agrupadas, nunca exibidas como resultados independentes.
- Protótipos `ideathon/materiais/inspirations/juridico_wallace/` marcam trechos revogados inline ("(Revogado pela Lei nº 11.941, de 2009)") e usam "Vigência e atualidade" como critério de ranking, mas não modelam família/versão.
- Plano, linha 129: `GET /v1/documents/{id}` exige `version`.
- Protótipo `Busca_Regulatoria_Setor_Eletrico_prototipo.html`: o JS contém uma tela `network` (`buildNetworkSVG`, `networkRows`, `goNetwork`) com grafo em estrela e tabela normA / relação / normB / dispositivos, mas nenhuma marcação a renderiza e ela não está no menu. A tela de detalhe traz "Normas Relacionadas" e o card traz "Relacionado a:" como strings soltas, sem navegação.
- Protótipo: marcador "📌 Trecho relevante" no texto integral; histórico por artigo inline com redações antigas empilhadas.

## Decisions

- 2026-09-25 (issue-28, Eduardo): a lista de resultados carrega 10 famílias por vez, sob demanda; lotes são acrescentados e nunca reordenam o que já está na tela.
- 2026-09-25 (issue-28, Eduardo): a contagem exibida vem de `total` no envelope, não do número de cards carregados; o gatilho de "carregar mais" é alcançável por teclado.
- 2026-09-25 (issue-28, Eduardo): `corpus_version` mais recente gera aviso com ação de refazer a busca; a lista aberta nunca recebe resultados de outro corpus.

- 2026-09-18 (issue-3): face do card = versão mais recente da família; trecho casado etiquetado pela sua versão.
- 2026-09-18 (issue-3): sugestão pendente visível no card como aviso + atalho de confirmação, sem alterar o agrupamento; data de coleta marcada como tal quando usada como fallback.
- 2026-09-18 (issue-5): sem tela de grafo global no TB1; a exploração é um painel "Relações" egocêntrico de um salto, recentrável, na página da família e na página do processo.
- 2026-09-18 (issue-5): página da família = cabeçalho + linha do tempo de versões (mais recente selecionada) + texto da versão selecionada com trechos casados destacados e etiquetados + painel "Relações". Sem histórico por artigo, sem diff entre versões.
- 2026-09-18 (issue-5): processo SEI tem página própria (peças por data, cadeia `responde_a` visível, painel "Relações").
- 2026-09-18 (issue-5): confirmação de aresta sugerida e de fusão de família é inline na página do documento, não em fila de revisão.

## Derived requirements and constraints

- A resposta de `search` por família inclui: `family_id`, versão mais recente (título, data, vigência), e a lista de chunks casados com `document_version`, `excerpt`, localizador e score.
- O card indica quando o trecho casado pertence a uma versão que não é a mais recente (isto cobre o caso de a família ter casado só em versões superadas).
- O card mostra aviso de sugestão de fusão pendente com ação de aceitar/rejeitar; a ação registra autoria.
- A data exibida no card indica sua origem quando é data de coleta e não de publicação.
- Abrir o card leva ao objeto-documento com a versão mais recente selecionada e as demais navegáveis.
- A página da família consome `GET /v1/documents/{id}?version=` (plano, linha 129) para a versão selecionada e precisa de uma operação que liste as versões da família e outra que devolva as arestas de um nó com tipo, estado, evidência e score (contrato a detalhar na F3; a issue #15 tirou `get_document` do port — o backend serve metadados do próprio catálogo e o texto extraído pelo localizador, [[i4-storage]]; do port vêm só os candidatos de relação).
- O painel "Relações" agrupa arestas por tipo (`pertence_ao_processo`, `referencia`, `revoga`, `altera`, `responde_a`, `regula`, `similar_a`) e distingue visualmente `confirmed`, `suggested` e pendente de alvo.
- Clicar num nó vizinho navega para a página dele (família ou processo) com o painel recentrado; nenhuma tela mostra mais de um salto de uma vez.
- A página do processo SEI lista as peças por data e desenha a cadeia `responde_a` entre elas.
- Trecho destacado no texto da versão selecionada leva a etiqueta da versão; se o trecho casou só numa versão superada, a linha do tempo indica em qual e permite abri-la.

## Open questions

- Desenho visual final (cores, densidade, layout responsivo) do card, da linha do tempo e do painel "Relações": trabalho de F1 na implementação, não decisão de especificação.
- Diff entre versões de uma família: fora do TB1; entra se a Carolina pedir ao revisar o caso.

## Evidence

- Map issue #1, Notes (decisões de 2026-09-17).
- `ideathon/materiais/inspirations/juridico_wallace/Busca_Regulatoria_Setor_Eletrico_prototipo.html` (marcação de revogação; critério de vigência).
- Mesmo protótipo, template descompactado (bundle gzip+base64): tela `network` não ligada, "Normas Relacionadas" sem navegação, marcador "Trecho relevante", histórico por artigo inline.
- Issue #4 / [[d14-data-operations-modeling]] e [[i10-hybrid-decision-intelligence]]: nós, tipos e estados de aresta que o painel "Relações" expõe.

## Topic history

- issue-3: fixou um card por família com a versão mais recente como face, trechos etiquetados por versão, e o aviso de sugestão de fusão pendente no card.
- issue-5: fixou a página da família (cabeçalho, linha do tempo, texto da versão selecionada, painel "Relações" egocêntrico de um salto), a página do processo SEI, a ausência de grafo global e a confirmação inline de sugestões.
