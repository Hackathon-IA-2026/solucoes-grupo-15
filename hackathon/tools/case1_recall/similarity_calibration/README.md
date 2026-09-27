# Recalibração de `limiar_relacao`/`limiar_fusao` com embeddings REAIS do caso 1 (issue #74)

Reexecuta a calibração da issue #61
(`hackathon/tools/prototypes/family_similarity/`) — mas lendo os vetores
que o serviço `ai` realmente persistiu ao indexar o corpus real do caso 1
(issue #73, `EMBEDDER=bedrock`, Postgres/OpenSearch locais), não mais os
embeddings do protótipo do Recall@3 (issue #60), que chamava o Bedrock
diretamente num script isolado.

**Nota de escopo (mesma da #73/#74):** MVP de 10 documentos do caso 1, não
o corpus completo — os dois pontos abertos pela #61 seguem valendo sobre o
mesmo corpus pequeno, agora com os embeddings reais em vez dos do
protótipo.

## Fonte dos vetores

`hackathon/.pipeline-output/documents/_raw_vectors/amazon.titan-embed-text-v2-us-east-1-1024d-normalized.jsonl`
— vetores brutos persistidos por `RawVectorStore` (issue #73,
`hackathon/ai/app/raw_vectors.py`) durante as execuções reais de
`hackathon/tools/case1_recall/seed_and_measure.py`. Formato JSONL
append-only com tombstones; o replay (`RawVectorStore.load_all`, que
decide quais chunks estão "vivos" depois de reindexações) é reaproveitado
diretamente do módulo `ai`, nunca reimplementado aqui.

Nenhum script deste pacote faz chamada nova ao Bedrock/AWS — só leem o
arquivo já commitado.

## O que mudou desde a #61 e o que não mudou

- **Fonte dos embeddings**: agora o caminho real de produção
  (`ai/app/chunking.py` + `ai/app/embeddings.py`, via `/internal/v1/index`),
  não mais o script isolado do protótipo #60.
- **Chunking**: `ai/app/chunking.py` é uma port quase verbatim do
  protótipo `recall_baseline/chunking.py` (issue #69) — mesmos parâmetros
  (600/800/100 tokens, `tiktoken cl100k_base`, heurísticas de
  heading/tabela), mesmo texto de entrada (`.md` extraído da #59). A
  contagem de chunks por família bate exatamente com a do protótipo (342
  chunks, 10 famílias, mesma distribuição por família) — não é uma
  reprodução aproximada, é a mesma entrada processada pelo mesmo
  algoritmo.
- **Resultado**: a matriz de 45 pares reproduz, casa a casa, os mesmos
  scores do protótipo (ex.: par positivo conhecido 0,8062, par de
  controle 0,8368, teto 0,9278 — ver `output/family_similarity.json`).
  Isso é esperado e não é um erro: Titan V2 é determinístico e a entrada
  de texto é idêntica; a recalibração ainda vale porque agora repousa na
  cadeia real de produção (`ai` real, vetores persistidos fora do índice,
  reindex comprovado sem AWS pela #73), não mais num script que nunca
  toca o código de produção.
- **Vocabulário**: pós-#64, o agrupamento por família saiu da
  visualização/busca (`family_id` permanece só como atributo de
  filtro/dado no envelope) — este pacote usa "família" apenas no sentido
  de D4 (identidade lógica de uma peça documental), nunca como unidade de
  agrupamento na API.

## Pipeline

```
_raw_vectors/…jsonl (342 chunks reais, 10 documentos, replay de tombstones via RawVectorStore)
  -> um vetor por família: média dos embeddings dos chunks do documento,
     renormalizada para norma unitária          (family_vectors.py)
  -> matriz de similaridade (produto interno / cosseno) entre as 10 famílias,
     45 pares únicos                             (compute_similarity.py)
  -> top_k=3 vizinhos mais próximos por família   (compute_similarity.py)
  -> classificação de cada par em sem_relacao / similar_a / sugestao_fusao,
     distribuição por bucket (mesmo processo / mesmo tema / temas diferentes)
                                                   (calibrate_thresholds.py)
  -> avaliação da alternativa "vetor só de motivação"
                                                   (evaluate_aggregation_alternative.py)
```

## Rodar

```bash
cd hackathon/tools/case1_recall/similarity_calibration
python3.12 compute_similarity.py               # matriz + top-3 -> output/family_similarity.json
python3.12 calibrate_thresholds.py             # classificação + distribuição -> output/calibration_report.json
python3.12 evaluate_aggregation_alternative.py # evidência da decisão de agregação -> output/aggregation_alternative_report.json
python3.12 family_vectors.py                   # (opcional) só confere os 10 vetores e suas normas
```

## AC — busca explícita por par de fusão real (republicação/retificação)

O corpus real indexado pela #73 continua sendo os mesmos 10 `document_version`
`case1-*` da fixture demo (`CASE1_EXPECTED_DOCUMENT_COUNT = 10`,
`hackathon/backend/app/fixtures/case1_loader.py`) — nenhuma peça nova, nenhuma
versão retificada/republicada foi adicionada entre a #61 e a #73. **Ausência
confirmada novamente, agora sobre os vetores reais**: não existe, nos dados
reais disponíveis, nenhum par que devesse cruzar `limiar_fusao` — é a mesma
lacuna conhecida do corpus já registrada em D14 ("Open questions"), não um
erro deste protótipo, e não bloqueia este ticket (previsto no próprio AC).

## AC — distribuição de similaridade por bucket (embeddings reais)

Buckets definidos por `family_labels.py` (mesma agregação de processo do D16,
`process_aggregation.py`): `mesmo_processo` (mesmo `process_group`),
`mesmo_tema` (mesmo `document_type`, processo diferente), `temas_diferentes`
(o resto). Ver `output/calibration_report.json`, `distribution_by_bucket`:

| bucket | n | min | max | mean | median |
| --- | ---: | ---: | ---: | ---: | ---: |
| `mesmo_processo` | 12 | 0,7681 | 0,9278 | 0,8576 | 0,8696 |
| `mesmo_tema` (processo diferente) | 7 | 0,6023 | 0,8368 | 0,7084 | 0,7051 |
| `temas_diferentes` | 26 | 0,5319 | 0,7881 | 0,6752 | 0,6868 |

Leitura: pares do mesmo processo dominam a faixa alta (mediana 0,87), como
esperado (mesmos fatos/partes). O bucket `mesmo_tema` tem o teto mais alto
fora do `mesmo_processo` (0,8368 — o par de controle auto×auto da #61,
achado inesperado reproduzido aqui) e também os pisos mais baixos entre os
três buckets (0,6023) — confirma que "mesmo gênero documental" por si só não
é um preditor consistente de similaridade, na linha do achado já registrado
em D14/#61.

## AC — limiares reconfirmados

`limiar_relacao = 0.80`, `limiar_fusao = 0.97`, `top_k = 3` — **mantidos sem
alteração**. Evidência (`output/calibration_report.json`):

- Par positivo conhecido (`case1-coelba-recurso` ↔ `case1-coelba-complemento`,
  referência textual explícita confirmada na #61): score **0,8062**,
  classificado `similar_a` — critério de aceite satisfeito.
- Par de controle (`case1-cemig-auto` ↔ `case1-enel-auto`, casos não
  relacionados): score **0,8368**, também `similar_a` — o mesmo achado
  inesperado da #61 (gabarito administrativo rígido dos autos de infração)
  reproduzido aqui com os embeddings reais.
- Maior score entre quaisquer duas famílias distintas: **0,9278**
  (`case1-cemig-recurso` ↔ `case1-cemig-voto`, mesmo processo) — `0,042`
  abaixo de `limiar_fusao = 0,97`, mesma margem da #61.
- Classificação final: **34** `sem_relacao`, **11** `similar_a`, **0**
  `sugestao_fusao` — números idênticos aos da #61.

**Confiança desta calibração**: menor do que uma calibração contra um corpus
maior e um positivo real de fusão — os embeddings agora vêm do caminho real
de produção, mas continuam sobre a **mesma amostra de 10 documentos** da #61
(nenhum documento novo, nenhum par de fusão real disponível). A recalibração
confirma que a cadeia real de produção reproduz o resultado do protótipo,
não que a amostra ficou maior ou mais representativa. Revisitar quando um
caso real de republicação/retificação aparecer no corpus maior (#56) ou em
dados futuros — mesma ressalva já registrada em D14 desde a #61.

## AC — estratégia de vetor de agregação

**Decisão: mantida** a média de todos os chunks da família, renormalizada
(`family_vectors.py::_mean_vector`) — a mesma escolha da #61. A alternativa
levantada pela própria issue #74 ("ex.: só o trecho de fundamentação") foi
avaliada e **não adotada**, com evidência
(`output/aggregation_alternative_report.json`,
`evaluate_aggregation_alternative.py`):

- Sob a heurística de heading real do chunker de produção
  (`ai/app/chunking.py`), só **3 das 10 famílias** têm algum chunk cuja
  seção bate com "motivação"/"fundamentação"/"mérito" — as três do tipo
  `auto_de_infração`/`exposição_de_motivos` (seção `"III – DA MOTIVAÇÃO"`
  no auto, por exemplo). As 7 famílias de `recurso_administrativo`, `voto`
  e `complementação_de_recurso` não têm nenhum chunk classificado nessa
  seção — usam outras convenções de título que a heurística de heading
  atual não reconhece (ou não têm heading, ficando com `section = None`).
- **Achado decisivo**: o **par positivo conhecido mandatado pela própria
  issue** (`case1-coelba-recurso` ↔ `case1-coelba-complemento`) não tem
  vetor "só motivação" calculável para **nenhum dos dois lados** — a
  alternativa não pode nem ser comparada contra o critério de aceite que
  ela deveria ajudar a satisfazer.
- No único par onde a alternativa é calculável dos dois lados (o próprio
  par de controle, `case1-cemig-auto` ↔ `case1-enel-auto`), ela **reduz**
  a similaridade de 0,8368 para **0,6881** — um sinal real, não ruído:
  restringir a autos de infração à seção de motivação de fato separa
  melhor dois casos não relacionados do mesmo gênero documental. Mas isso
  não a torna adotável agora, justamente pelo ponto anterior.

Registrado como pista para uma futura vetorização por seção — se/quando o
chunker de produção ganhar uma classificação de seção consistente também
para recursos, votos e complementações (não é o caso hoje) — mas **não
adotada nesta calibração**: usar uma agregação que nem sequer é computável
para o par que a issue pede para capturar seria pior do que manter a média
de todos os chunks.

## Arquivos

- `family_labels.py` — metadados legíveis (tipo documental, identificador
  oficial, agente, grupo de processo D16) das 10 famílias reais,
  reindexado pelas chaves `family_id` de produção (`case1-<agente>-<tipo>`).
- `family_vectors.py` — carrega os vetores brutos reais via
  `RawVectorStore` (módulo `ai`), agrega por `family_id`, calcula o vetor
  médio renormalizado e (quando existir) o vetor alternativo "só
  motivação".
- `compute_similarity.py` — matriz de similaridade completa (45 pares) e
  top-3 vizinhos por família -> `output/family_similarity.json`.
- `calibrate_thresholds.py` — classifica os 45 pares pelos limiares
  vigentes, com distribuição por bucket e pares conhecidos anotados ->
  `output/calibration_report.json`.
- `evaluate_aggregation_alternative.py` — evidência da decisão sobre a
  estratégia de vetor de agregação -> `output/aggregation_alternative_report.json`.
- `output/` — commitado (mesma decisão da #61: corpus público,
  reprodutibilidade da calibração). Sem credenciais.
