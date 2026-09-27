# PROTOTYPE — Vizinhança vetorial entre famílias e calibração de `limiar_relacao`/`limiar_fusao` (issue #61)

Protótipo terminal que calcula a vizinhança vetorial entre as 10 famílias
do corpus real (`hackathon/data/case-1-carolina-mmgd/`) e calibra os dois
limiares ordenados decididos em D14
(`requirements/perspec-me/capiwatt-lens-hackathon/concerns/d14-data-operations-modeling.md`,
"Vizinhança vetorial"; `limiar_relacao < limiar_fusao`) contra pares
conhecidos do corpus, validados diretamente no texto dos documentos.

Não faz **nenhuma chamada nova ao Bedrock**: reaproveita os 342 embeddings
de chunk já calculados pelo protótipo `recall_baseline` (issue #60, commit
`fc24089`), lidos de
`hackathon/tools/prototypes/recall_baseline/output/chunks.jsonl`.

## O que "família" significa neste corpus

Cada um dos 10 `.md`/PDFs do corpus é uma família própria (uma peça
distinta) — não há, nestes dados, duas versões republicadas/retificadas da
mesma peça (ver `d4-data-dictionary.md`: família = identidade lógica de UMA
peça documental; processo SEI ≠ família). Logo:

- `document_id` em `chunks.jsonl` **já é** a chave de família para este
  corpus — não há um passo separado de "resolver family_id" a rodar aqui.
- A vizinhança vetorial é calculada **entre as 10 famílias** (uma por
  documento), nunca entre processos.
- Não existe, nos dados reais disponíveis, nenhum par que devesse cruzar
  `limiar_fusao` — isso é uma lacuna conhecida do corpus (ver D14, "Open
  questions"), não um erro deste protótipo.

## Pipeline

```
recall_baseline/output/chunks.jsonl (342 chunks, 10 documentos, embeddings Titan V2)
  -> um vetor por família: média dos embeddings dos chunks do documento,
     renormalizada para norma unitária          (family_vectors.py)
  -> matriz de similaridade (produto interno / cosseno) entre as 10 famílias,
     45 pares únicos                             (compute_similarity.py)
  -> top_k=3 vizinhos mais próximos por família   (compute_similarity.py)
  -> classificação de cada par em sem_relacao / similar_a / sugestao_fusao
     pelos limiares calibrados                    (calibrate_thresholds.py)
```

## Configuração do modelo (travada, não é decisão deste protótipo)

Mesma config de #59/#60: `amazon.titan-embed-text-v2:0`, região
`us-east-1`, 1024 dimensões, vetores normalizados. Métrica de similaridade:
produto interno entre vetores unitários (== cosseno), mesma métrica de #60,
por consistência.

## Escolha de engenharia: um vetor por família

A issue deixa em aberto *como* obter um único vetor por família a partir
dos chunks já existentes. Escolha feita aqui: **média dos embeddings dos
chunks do documento, renormalizada para norma unitária** (`family_vectors.py`).

Por quê:

- **Zero chamadas novas ao Bedrock** — os 342 embeddings de chunk já
  existem, reais, de uma execução com credenciais reais (#60). Reembedar o
  documento inteiro também estouraria o limite de entrada do Titan para os
  dois documentos maiores (57 e 71 páginas no PDF original).
- Uma média estrutural sobre texto já estruturalmente chunkado é uma forma
  padrão e defensável de obter um vetor por documento, sem inventar uma
  etapa nova de sumarização (que D14/#60 não pediu e que teria sua própria
  calibração em aberto).
- Um excerto isolado (ex.: só a primeira página) sub-representaria
  documentos longos e multi-seção (até 81 chunks num único auto de
  infração) e enviesaria o vetor da família para o cabeçalho/boilerplate.
- A média de vetores unitários não é, em geral, unitária — por isso é
  renormalizada (dividida pela própria norma L2) antes de ser usada, para
  manter produto interno == cosseno também no nível de família.

Todos os `n_chunks` por família aparecem em `output/family_similarity.json`
(mínimo 7 chunks para a complementação, máximo 81 para o maior auto de
infração).

## Verificação dos pares conhecidos

A issue #61 propõe hipóteses de trabalho para calibração e pede
explicitamente para validá-las contra o conteúdo real, não confiar cegamente
na lista. Verificação feita, lendo os `.md` extraídos:

- **Par fortemente relacionado** — `recurso-48500.009907-2025-96` e
  `complementacao-recurso-48500.017555-2025-42`: **confirmado**. A
  complementação (26/05/2025) cita explicitamente "complementar o recurso em
  face do Auto de Infração – AI – nº 0035/2025-SFT" e retoma textualmente o
  pedido "ii)" e as "RAZÕES DA RECORRENTE apresentadas por meio da carta RTC
  – NCLB 022/2025 de 20/03/2025" — que é exatamente o cabeçalho do próprio
  recurso `48500.009907-2025-96` ("RTC – NCLB 022/2025", "Salvador, 20 de
  março de 2025"). Referência textual inequívoca, mesmo caso Coelba/AI
  0035/2025-SFT, tipos documentais diferentes (`recurso_administrativo` vs
  `complementacao_de_recurso`) — família distinta, candidato a `similar_a`,
  nunca fusão. (Nota lateral: essa mesma citação também alimenta uma aresta
  `referencia` explícita por identificador, issue #4 — a vizinhança vetorial
  calibrada aqui é evidência complementar, não a única.)
- **Pares do mesmo processo, tipos diferentes** (auto+recurso+voto de
  `48500.004024-2017-80` e de `48500.000639-2019-07`; auto+voto+recurso+
  complementação do grupo Coelba `48500.901433-2024-53`): **confirmado**
  como mesmo caso/mesmas partes pelos cabeçalhos e conteúdo (mesmo agente,
  mesmo AI, mesmos fatos). Famílias claramente distintas (tipos e
  identificadores oficiais diferentes).
- **Par de controle sem relação conhecida** (auto de infração de
  `48500.004024-2017-80`, Enel Ceará, vs. auto de infração de
  `48500.000639-2019-07`, Cemig): **confirmado como casos não relacionados**
  no conteúdo (agentes, fatos e processos totalmente distintos — grep pelos
  nomes das distribuidoras não encontra nenhuma menção cruzada). **Mas a
  hipótese de que este par teria baixa similaridade vetorial não se
  confirmou** — ver "Achado inesperado" abaixo.
- **Nenhum par de fusão real no corpus**: confirmado — os 10 documentos são
  10 famílias distintas por construção (ver acima), sem nenhuma peça
  duplicada/retificada.

## Achado inesperado (documentado, não escondido)

A hipótese de controle da própria issue não se confirmou na matriz real: o
par "auto de infração Enel Ceará" × "auto de infração Cemig" — dois casos
comprovadamente não relacionados no conteúdo — tem **score 0.8368**, mais
alto que o do par verdadeiramente relacionado recurso×complementação
(**0.8062**). Está inclusive entre os 10 pares mais similares de toda a
matriz de 45 pares.

Explicação mais provável, olhando a matriz completa
(`output/family_similarity.json`): autos de infração da ANEEL seguem um
gabarito administrativo muito rígido (mesmas seções, mesma linguagem de
enquadramento, mesmas tabelas de conformidade, mesmos dispositivos
regulatórios citados) que se repete de processo para processo,
independentemente do caso concreto — muito mais rígido do que o texto de
recursos (escrito por advogados diferentes, mais idiossincrático) ou mesmo
de votos. Isso aparece nos próprios dados: pares "auto × auto" entre
processos diferentes ficam consistentemente na faixa 0.74–0.84 (as três
combinações cruzadas: 0.8368, 0.7630, 0.7422), enquanto pares "recurso ×
recurso" cruzados ficam mais baixos (0.60–0.68) e pares envolvendo a
complementação (documento mais curto e específico, 7 chunks) cruzados com
documentos de outro processo ficam na faixa mais baixa observada
(0.53–0.62).

**Consequência prática**: com este vetor de família (média de chunks) não
existe um único limiar que separe perfeitamente "par com relação conhecida"
de "par sem relação conhecida" — o par positivo conhecido (0.8062) fica
*abaixo* de um par negativo conhecido (0.8368). A calibração abaixo é a
escolha defensável dado esse fato, não uma separação perfeita.

## Matriz completa e vizinhos top-3

Ver `output/family_similarity.json` (todos os 45 pares e os top-3 vizinhos
de cada uma das 10 famílias) e `output/calibration_report.json` (mesmos
pares já classificados pelos limiares calibrados).

Os 10 pares de maior score (de 45):

| score | par | mesmo grupo de processo |
| ---: | --- | :---: |
| 0.9278 | recurso 000639 ↔ voto 000639 | sim |
| 0.9091 | auto 004024 ↔ voto 004024 | sim |
| 0.9068 | auto 000639 ↔ voto 000639 | sim |
| 0.9009 | auto 000639 ↔ recurso 000639 | sim |
| 0.8752 | auto 901433 ↔ voto 901433 | sim |
| 0.8726 | recurso 009907 ↔ auto 901433 | sim (grupo Coelba) |
| 0.8666 | recurso 009907 ↔ voto 901433 | sim (grupo Coelba) |
| 0.8540 | auto 004024 ↔ recurso 004024 | sim |
| 0.8368 | auto 000639 ↔ auto 004024 | **não** (achado inesperado, acima) |
| 0.8235 | recurso 004024 ↔ voto 004024 | sim |
| 0.8062 | recurso 009907 ↔ complementação 017555 | sim (grupo Coelba; par positivo conhecido) |

Os 5 pares de menor score envolvem a complementação (017555) contra
documentos de processo diferente (0.5319–0.6183) — o piso empírico da
matriz.

## Calibração

**Valores calibrados (2026-09-26):**

| Parâmetro | Valor |
| --- | --- |
| `top_k` | 3 (já fixado, não é decisão desta issue) |
| `limiar_relacao` | **0.80** |
| `limiar_fusao` | **0.97** |

`limiar_relacao (0.80) < limiar_fusao (0.97)` — ordem exigida por D14
satisfeita.

### Por que `limiar_fusao = 0.97`

O maior score observado entre **quaisquer duas famílias distintas** em toda
a matriz é 0.9278 (recurso × voto do mesmo processo `48500.000639/2019-07`
— alta similaridade porque compartilham fatos e partes, mas são peças
inequivocamente diferentes). Não há, neste corpus, nenhum par que devesse
sugerir fusão (nenhuma família duplicada/retificada — ver acima). `0.97`
fica **0.042 acima** desse teto observado, com margem: uma peça
duplicada/retificada de fato (mesmo texto, poucas correções) deveria gerar
um vetor quase idêntico ao original (esperado > 0.99, muito mais próximo de
1.0 do que o teto de 0.93 observado entre as famílias mais parecidas que
ainda assim são claramente distintas). `0.97` é, portanto, um piso
defensável para "candidato a fusão" mesmo sem um positivo real disponível
para calibrar contra — exatamente a lacuna que a própria issue #61 já
antecipa e pede para documentar, não resolver.

### Por que `limiar_relacao = 0.80`

Com `limiar_relacao = 0.80`: 11 dos 45 pares caem na faixa `similar_a`
(entre os limiares) — ver tabela acima. Dez desses onze são pares
genuinamente do mesmo processo/caso (validados por leitura direta do
conteúdo). O par positivo conhecido explicitamente pedido pela issue
(recurso 009907 ↔ complementação 017555, score 0.8062) **fica capturado**
nessa faixa, satisfazendo o critério de aceite.

Dado o achado da seção anterior — não existe um único limiar que inclua
0.8062 e exclua 0.8368 — a escolha de `0.80` prioriza **não perder o par
positivo conhecido mandatado pela issue**, aceitando como trade-off
documentado que o par "auto Enel × auto Cemig" (0.8368, sem relação real)
também entra na faixa `similar_a`. Isso é aceitável porque `similar_a` é
**apenas uma aresta sugerida** no grafo de relações (D14) — nunca uma fusão
automática nem uma sugestão de fusão de família (D4: "a similaridade só
sugere fusão, nunca agrupa sozinha", e mesmo a sugestão de fusão exige
confirmação humana) — e o `top_k=3` já limita o número de sugestões por
família. Subir o limiar acima de 0.8368 para excluir esse falso positivo
excluiria também o par positivo conhecido (0.8062 < 0.8368), o que
contrariaria o critério de aceite da própria issue; descer o limiar abaixo
de 0.80 só adicionaria mais pares de similaridade-por-gênero
(auto × auto/voto × voto entre processos não relacionados) sem ganhar
nenhum par positivo adicional confirmado.

**Piso confirmado**: pares com score abaixo de 0.80 — a maioria dos 45
pares (34) — incluem todos os pares de controle validados como realmente
sem relação (recurso × recurso entre processos diferentes: 0.60–0.68;
qualquer par envolvendo a complementação contra outro processo: 0.53–0.62).
Nenhum desses gera aresta `similar_a` nem sugestão de fusão.

**Nenhum par cruza `limiar_fusao = 0.97`** neste corpus (`sugestao_fusao`:
0 pares) — consistente com a limitação conhecida de que não há, nos dados
reais disponíveis, nenhum par que devesse ser sugerido para fusão de
família.

## Limitação honesta (a mesma que a própria issue já antecipa)

Este corpus **não contém nenhum par positivo real de fusão** (nenhuma
família duplicada/retificada entre os 10 documentos). `limiar_fusao` foi
calibrado de forma defensável — acima do teto observado entre as famílias
mais parecidas que ainda assim são inequivocamente distintas, com margem
justificada — mas não contra um verdadeiro positivo, porque nenhum existe
nos dados disponíveis (D14, "Open questions": "calibrar com pares
conhecidos do corpus após a invocação funcional do modelo" — lacuna já
registrada ali, não introduzida por este protótipo). Quando um caso real de
republicação/retificação aparecer no corpus maior (#56) ou em dados
futuros, `limiar_fusao` deve ser revisitado contra esse positivo real.

Adicionalmente, e diferente do que a issue antecipava: o par de controle
proposto (mesmo tipo documental, casos não relacionados) **não** serviu de
piso negativo confiável — ver "Achado inesperado" acima. A vizinhança
vetorial por vetor médio de documento, neste corpus pequeno e homogêneo
(todos os documentos são peças administrativas/jurídicas da ANEEL sobre
fiscalização de MMGD), é sensível a similaridade de gênero/formato
(sobretudo entre autos de infração, que seguem um gabarito rígido) tanto
quanto a similaridade de conteúdo/caso. `limiar_relacao = 0.80` é calibrado
para não perder o único par positivo confirmado, aceitando esse ruído
conhecido na faixa `similar_a` (uma sugestão reversível, nunca uma fusão).

## Rodar

Os scripts leem `recall_baseline/output/chunks.jsonl` (já commitado, #60) e
**não fazem nenhuma chamada de rede** — não é necessário `source .env` nem
credenciais AWS para este protótipo.

```bash
cd hackathon/tools/prototypes/family_similarity
python3.12 compute_similarity.py      # matriz completa + top-3 vizinhos -> output/family_similarity.json
python3.12 calibrate_thresholds.py    # classifica os 45 pares pelos limiares calibrados -> output/calibration_report.json
python3.12 family_vectors.py          # (opcional) só confere os 10 vetores de família e suas normas
```

## Arquivos

- `family_vectors.py` — carrega `chunks.jsonl`, agrega por `document_id`
  (= família), calcula o vetor médio renormalizado por família.
- `family_labels.py` — metadados legíveis (tipo documental, identificador
  oficial, agente) das 10 famílias, só para relatório/leitura humana.
- `compute_similarity.py` — matriz de similaridade completa (45 pares) e
  top-3 vizinhos por família -> `output/family_similarity.json`.
- `calibrate_thresholds.py` — classifica os 45 pares pelos limiares
  calibrados, com os pares conhecidos anotados -> `output/calibration_report.json`.
- `output/` — commitado (mesma decisão do `recall_baseline`: corpus público,
  reprodutibilidade da calibração). Sem credenciais.
