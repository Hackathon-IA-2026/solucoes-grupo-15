# PROTOTYPE — Recall@3 baseline (issue #60)

This is a terminal prototype that measures `Recall@3` of the baseline
pipeline decided in M1/D14
(`requirements/perspec-me/capiwatt-lens-hackathon/concerns/m1-algorithm-model-selection.md`,
`d14-data-operations-modeling.md`) on the real 10-PDF corpus, against the
gabarito fixed in D16
(`requirements/perspec-me/capiwatt-lens-hackathon/concerns/d16-golden-dataset.md`).
It is a **real, end-to-end run** — no fixture, no simulated embeddings: it
reads the Markdown extraction produced by issue #59 (commit `c6a8370`),
chunks it, calls Amazon Bedrock for every chunk and for the test question,
ranks by similarity, and reports the metric.

## Pipeline

```
.md files (10, from #59)
  -> structural chunking (chunking.py)
  -> Titan V2 embeddings, one invoke_model per chunk + one for the query (embeddings.py)
  -> top-3 chunks by dot product similarity
  -> aggregate top-3 chunks by processo agregado (process_map.py, D16 NUP normalization)
  -> Recall@3 against the golden Top 3
```

## Configuration used (locked by M1, not a decision made here)

| Parameter | Value |
| --- | --- |
| `model_id` | `amazon.titan-embed-text-v2:0` |
| Region | `us-east-1` |
| Dimensions | `1024` |
| Normalization | `true` (unit-length vectors) |
| Similarity metric | dot product — with normalized vectors this is exactly cosine similarity; documented here because it is a free choice the ticket left open |
| Same config for documents and query | yes |
| `corpus_version` | `c6a8370` (the commit that produced the `.md` extraction consumed here, issue #59) |
| Tokenizer | `tiktoken`, encoding `cl100k_base` (see below) |
| Chunking target / max / overlap | 600 / 800 / 100 tokens |
| `top_k` | 3 |

### Tokenizer choice

`tiktoken` (`cl100k_base`) is used to count tokens for chunk sizing. It is
**not** the tokenizer Titan uses internally — Bedrock reports its own
`inputTextTokenCount` per call, which is recorded separately in the output
(`bedrock_input_token_count` per chunk, alongside `chunk_token_count_tiktoken`)
and the two numbers are close but not identical. The ticket's own instruction
was to pick *a* deterministic, documented tokenizer, not necessarily Titan's;
`tiktoken` was already installed for this interpreter (`python3.12 -c "import
tiktoken; print(tiktoken.__version__)"` → `0.11.0`), so no new dependency was
added. Given the same input text, this chunker always produces byte-for-byte
identical chunks.

### Chunking rules (`chunking.py`)

- Documents are split into **blocks** (heading / paragraph / table) on blank
  lines; a single short, mostly-uppercase line (e.g. `I – DA IDENTIFICAÇÃO`,
  `EXPOSIÇÃO DE MOTIVOS PARA O AUTO DE INFRAÇÃO`) is treated as a heading; a
  multi-line block where most lines have an internal run of 2+ spaces (the
  columnar layout `pdftotext -layout` produces for tables) is treated as a
  table; everything else is a paragraph.
- Blocks are accumulated into a chunk until the **target** (600 tokens) is
  reached, and a chunk never exceeds the **maximum** (800 tokens) — an
  oversized single block (table or paragraph) is itself split first: a table
  is split row-wise with its header line repeated at the top of every
  continuation piece; a paragraph is split on sentence boundaries.
- **Overlap** (100 tokens) is only seeded between two **adjacent narrative**
  chunks — i.e. the previous chunk ended on a paragraph block and the next
  block is also a paragraph. Crossing into a new heading/section, or into a
  table, starts a clean chunk with no overlap, per the D14/M1 decision
  ("sobreposição... apenas entre trechos narrativos adjacentes").
- Chunks never cross a document (`.md` file = one documental version here);
  since this corpus has exactly one version per document, this is automatic.
- Both the heading detector and the table detector are **heuristics**, not a
  real Markdown/HTML parser — the `.md` files are a verbatim `pdftotext
  -layout` copy, not semantic Markdown. See "Known limitations" below.

### Page metadata — a correction to the ticket's own assumption

Issue #60 anticipated that the `.md` files "já não tem marcação de página
original do PDF". That turned out not to be the case: the #59 prototype's
extraction (`pdf_to_markdown/extract_raw_text.py` + `filter_verbatim.py`)
keeps an `<!-- page:N -->` marker before every page's text, and no page was
ever dropped whole for any of the 10 documents (`pdf_to_markdown/README.md`,
"pages kept: N / N" for all ten) — so these markers line up with the original
PDF page numbers. This chunker uses them, and every chunk in `output/chunks.jsonl`
carries a real `page_start`/`page_end`. What is **still** out of scope here
(reserved for the future small-to-big ticket) is turning those page numbers
into a *rendering* of the full neighboring pages for context expansion —
`Recall@3` is measured strictly pre-expansion, on the chunks themselves.

## Metadata carried per chunk

`document_id`, `corpus_version`, `process_nup_raw` (corpus folder name),
`process_nup_canonical` (after D16 NUP aggregation, see below), `section`
(last heading seen before the chunk), `page_start`/`page_end`,
`chunk_token_count_tiktoken`, `bedrock_input_token_count`, the chunk `text`
itself, and its `embedding` (1024 floats). See `output/chunks.jsonl`.

## Process aggregation (`process_map.py`, per D16)

The corpus has 5 folders (one per NUP as filed) but only **3 processos
agregados** for evaluation: the Coelba recurso (`48500.009907/2025-96`) and
its complementação (`48500.017555/2025-42`) are the same Coelba/AI
`0035/2025-SFT` case as `48500.901433/2024-53` and are folded into it, never
counted as independent processes.

## Test question (D16, gabarito)

> procure precedentes sobre fiscalização de atendimento a solicitações de conexão de MMGD

Golden Top 3 (processo agregado): `48500.004024/2017-80`,
`48500.000639/2019-07`, `48500.901433/2024-53`.

## Run

From the repository root, with AWS credentials loaded (`.env`, never committed):

```bash
source .env
python3.12 hackathon/tools/prototypes/recall_baseline/run_recall_baseline.py
```

Unit tests for the deterministic chunking logic (no AWS calls):

```bash
python3.12 hackathon/tools/prototypes/recall_baseline/test_chunking.py
```

## Result of this run

- Corpus: 10 `.md` documents (`corpus_version=c6a8370`) → **342 chunks**
  (avg. ≈ 632 tokens, none over 800). 14 raw blocks in the corpus were
  themselves already over 800 tokens on their own before chunk assembly (11
  oversized paragraphs and 2 oversized tables in
  `auto-infracao-48500.000639-2019-07.md`/`auto-infracao-48500.004024-2017-80.md`,
  up to 1206 tokens) — these were split first by `_split_paragraph_block` /
  `_split_table_block` (sentence boundaries / table rows with header
  repeated) before chunk assembly, confirmed by an automated check that no
  resulting chunk exceeds 800 tokens.
- Query embedded: 21 Bedrock tokens, no error.
- All 342 chunks embedded: no error, 1024-dim unit vectors confirmed.
- Top-3 chunks retrieved (dot product / cosine):

  | score | processo agregado | documento | seção | páginas |
  | ---: | --- | --- | --- | --- |
  | 0.3751 | `48500.000639/2019-07` | auto-infração | Seção X – DAS OBRAS COM PARTICIPAÇÃO FINANCEIRA DO CONSUMIDOR | 6 |
  | 0.3686 | `48500.000639/2019-07` | recurso | (sem título de seção antes do trecho) | 11–12 |
  | 0.3638 | `48500.004024/2017-80` | auto-infração | III – DA MOTIVAÇÃO | 46–47 |

- Processos agregados no top-3: `{48500.000639/2019-07, 48500.004024/2017-80}`
  (só 2 processos distintos aparecem, porque os dois primeiros chunks do
  top-3 pertencem ao mesmo processo).
- Gabarito D16: `{48500.004024/2017-80, 48500.000639/2019-07, 48500.901433/2024-53}`.
- **`Recall@3 = 2/3 ≈ 0.667`**.
- **Gate `Recall@3 >= 2/3`: PASSOU.**

Full machine-readable result: `output/results.json`. Full chunk set with
text and embeddings: `output/chunks.jsonl`. Query embedding:
`output/query.json`.

Per M1's own decision, since the gate passed, the ~400/~800-token chunk-size
comparison and the alternative-model trial (Cohere Embed V4 / Nova Multimodal
Embeddings) are **not** triggered and were not attempted.

## Known limitations

- The heading/table detection in `chunking.py` is a heuristic over verbatim
  `pdftotext -layout` text (uppercase-ratio for headings, columnar-space-run
  ratio for tables), not a semantic parser — a rare ALL-CAPS short sentence
  could be misread as a heading, or a very sparse table could be misread as
  prose. Given the small corpus (10 documents, 342 chunks) this was not
  spot-checked line by line beyond the automated tests in `test_chunking.py`
  and the token-budget/page-tracking checks run during development.
- `recurso-48500.000639-2019-07.pdf` has one page (24) with visibly degraded
  OCR/text-layer extraction, inherited from the #59 extraction (documented in
  `pdf_to_markdown/README.md`, "Known limitation"). It did **not** affect
  this run's top-3 result (the retrieved chunk from that document covers
  pages 11–12, not 24), but any future query that happens to rank a chunk
  from page 24 highly would inherit that degradation.
- `Recall@3` here is computed strictly pre-expansion, over chunk-level hits
  only, per D14/M1's explicit separation from the small-to-big page
  expansion (a later ticket).
- The `output/` directory is committed to the repository (not
  `.gitignore`d) per this ticket's own instruction — the corpus is public
  (`hackathon/data/case-1-carolina-mmgd/README.md`: "Todos os documentos
  enviados foram informados como públicos"), and reproducibility of a
  Recall@3 measurement benefits from keeping the exact chunks/vectors this
  run used. No AWS credentials are stored in these files.
