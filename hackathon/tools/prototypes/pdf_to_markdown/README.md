# PROTOTYPE — PDF → Markdown extraction (issue #59)

This is a terminal prototype that implements the PDF → Markdown extraction
step decided in D14 (`requirements/perspec-me/capiwatt-lens-hackathon/concerns/d14-data-operations-modeling.md`,
"Etapa de extração por IA, antes do chunking"): before the structural
chunking pipeline runs, every PDF passes through an AI that copies the main
content verbatim into a `.md` file and removes whole attachments (vistoria
report, laudo técnico), "contrato social", and signatures/identification of
who signed.

## Approach chosen: script-assisted extraction, agent as the filtering AI

D14 leaves open *how* the AI tells "conteúdo principal" from "anexo" apart
inside the PDF. This prototype uses **option 1** from the issue's own list of
reasonable alternatives: a deterministic tool extracts the text, and the
filtering judgment (what counts as an attachment/contrato
social/signature, where each one starts and ends) is made by the agent doing
this implementation session — not by a second Bedrock model call. Two
reasons, both practical for a `wayfinder:prototype` ticket:

1. Bedrock in this account only has confirmed access to
   `amazon.titan-embed-text-v2:0` (embeddings). There is no confirmed
   text-generation model available (see the ticket's own instructions to
   check `aws bedrock list-foundation-models` before investing time in that
   path) — going through Bedrock for a generation step would be genuinely new
   ground, not a documented path already available for this project.
2. Doing the mechanical extraction with a deterministic tool
   (`pdftotext -layout`) and then only ever *deleting* clearly-identified
   lines/blocks — never rewriting a sentence — is a stronger guarantee of
   "cópia verbatim, nunca resume/parafraseia" than asking a generative model
   to reproduce the text from scratch, which always carries some risk of
   silently paraphrasing or dropping a clause.

**This session's role (the agent) was exactly the "IA de filtragem" D14
describes**: the raw per-page text of all 10 PDFs was read in full, the
boundary between main content and attachment/contrato-social/signature was
decided by that reading, and the decisions were written down as explicit,
auditable per-document specs (below) rather than made ad hoc while
retyping text.

## Two-step pipeline

### Step 1 — `extract_raw_text.py` (mechanical, no judgment)

```powershell
python hackathon/tools/prototypes/pdf_to_markdown/extract_raw_text.py `
  --pdf "hackathon/data/case-1-carolina-mmgd/48500.004024-2017-80/auto-infracao-48500.004024-2017-80.pdf" `
  --out "hackathon/.prototype-downloads/pdf-to-markdown/auto-infracao-48500.004024-2017-80.raw.txt"
```

Calls `pdftotext -layout` page by page (`/usr/bin/pdftotext`, poppler-utils)
and writes one text file with `<!-- pdftotext:page N -->` markers between
pages. This step never removes or rewrites anything — it is the byte-for-byte
verbatim baseline that step 2 only ever subtracts from.

`-layout` was chosen over a Python PDF library because all 10 real PDFs in
`case-1-carolina-mmgd/` are native text-layer PDFs (not scans) with columns,
tables and headers/footers; `-layout` preserves reading order well enough for
a human/LLM filtering pass, with no extra dependency beyond poppler-utils,
already present on this machine.

### Step 2 — `filter_verbatim.py` (applies the removal decisions)

```powershell
python hackathon/tools/prototypes/pdf_to_markdown/filter_verbatim.py `
  --raw "hackathon/.prototype-downloads/pdf-to-markdown/auto-infracao-48500.004024-2017-80.raw.txt" `
  --out "hackathon/data/case-1-carolina-mmgd/48500.004024-2017-80/auto-infracao-48500.004024-2017-80.md" `
  --spec "hackathon/tools/prototypes/pdf_to_markdown/specs/auto-infracao-48500.004024-2017-80.json"
```

Everything **not** matched by a removal rule is copied through character for
character. Three kinds of removal are supported:

- `drop_pages` (spec) — drop a whole page: for a full embedded attachment
  (vistoria report, laudo técnico) or a "contrato social" section, when a PDF
  embeds one as its own range of pages. **Unused for all 10 current PDFs** —
  see "What was actually found in this corpus" below.
- built-in regexes for boilerplate that repeats near-identically across the
  whole corpus: the SICNET/SEI per-page signature/certification footer
  (`Documento assinado digitalmente...` / `Documento assinado eletronicamente
  por ... código verificador ...`), the `(Assinado digitalmente)` /
  `(Assinatura digital)` stamp plus the two or three lines right after it
  (the signer's name and role), and a page-margin process-number stamp — but
  only when it is the page's very first non-blank line, which is how it
  behaves as a stamp; the same-shaped number appearing later in a page (e.g.
  a footnote's reference target) is left alone.
- per-document spec fields (`drop_line_literals`, `drop_line_contains`,
  `strip_trailing_rubric_tokens`) for the boilerplate that is specific to one
  PDF — a reviewer's rubric initials repeated on every page, an ICP-Brasil
  digital-signature stamp that `pdftotext -layout` merges into a garbled
  multi-column block, or an embedded exhibit's own signature. Every spec file
  under `specs/` has a `notes` field explaining *why* each pattern is there —
  read them before trusting a new document's output blindly.

## What was actually found in the 10 real PDFs

Before writing any removal rule, the raw text of all 10 PDFs in
`hackathon/data/case-1-carolina-mmgd/` was searched for "contrato social",
"laudo técnico", "relatório de vistoria" (and close variants/typos) as
section headers. **None of the 10 PDFs embeds a full separate attachment of
that kind as its own text section** — they *reference* an attached vistoria
report or Relatório de Fiscalização by name repeatedly (e.g. "conforme
Relatório de Fiscalização RF-0039/2017-SFE"), but the report/laudo itself
was sent to ANEEL as a different SICNET/SEI document, not bundled into these
particular PDFs. So `drop_pages` exists in the tool (for the larger corpus of
issue #56 or future documents that do embed one) but was not needed here.

What *is* present on every single page of all 10 PDFs is signature and
certification boilerplate — this is what most of the removal work does:

- **SICNET-era documents** (up to ~2023): a page-margin process-number stamp,
  a `Documento assinado digitalmente.` / `Consulte a autenticidade deste
  documento em http://sicnet2.aneel.gov.br/... código de verificação ...`
  footer on every page, and on the true final page a `(Assinado digitalmente)`
  / `(Assinatura digital)` stamp with the signer's name and role, sometimes
  followed by a one-line `Documento assinado digitalmente por <nome>, em
  <data> às <hora>` variant.
- **SEI-era documents** (2024/2025): a `SEI <processo> / pg. N` running
  footer, and at the end a `Documento assinado eletronicamente por <nome>,
  <cargo>, em <data>, às <hora>, ...` paragraph plus an authenticity
  paragraph and a `Referência: Processo nº ...` line.
- **Per-document extras**, each documented in its `specs/*.json`:
  - `auto-infracao-48500.004024-2017-80.pdf`: a "CECL" rubric (the SFE
    representative's initials) repeated on every page.
  - `recurso-48500.009907-2025-96.pdf` and
    `complementacao-recurso-48500.017555-2025-42.pdf`: the cover letter's
    ICP-Brasil digital-signature stamp, which `pdftotext -layout` renders as
    a garbled multi-column block (certificate id, timestamp with a `-03'00'`
    offset) immediately followed by the signer's name and role; also a
    reviewer-initials rubric (`MHS`, `FLM`).
  - `recurso-48500.000639-2019-07.pdf`: the petition's own closing signature
    (ICP-Brasil certificate fragments + name/role + letterhead footer), an
    **embedded email exchange reproduced as evidence** near the end of the
    document, whose two closing signature blocks (name, role, department,
    company, phone, personal email) are removed — but the email routing
    headers (De/Para/Cc/Assunto) and message bodies are kept verbatim,
    because that correspondence is the substantive evidence the recurso
    argument relies on (proof of when a reimbursement happened), not a
    signature; and one page (24) whose text-layer extraction is visibly
    degraded/garbled (see "Known limitation" below).

## Side-by-side demonstration

`hackathon/data/case-1-carolina-mmgd/48500.004024-2017-80/auto-infracao-48500.004024-2017-80.pdf`,
page 1, the cover Auto de Infração form. **Before** (`pdftotext -layout`
output, i.e. what the PDF actually contains, reading order preserved):

```
    7. REPRESENTANTE DO ÓRGÃO FISCALIZADOR

    NOME:                                Carlos Eduardo Carvalho Lima

    CARGO/FUNÇÃO:                        Superintendente Adjunto                           MATRÍCULA nº                     2549785

    ASSINATURA:

    Conforme art 34 da resolução normativa ANEEL n°63 de 12 de maio de 2004, o recurso deverá ser dirigido a autoridade que proferiu a decisão, acima identificada, a qual, se
    não a reconsiderar, no prazo de 5 (cinco) dias, o encaminhará a diretoria da ANEEL, que poderá confirmar, modificar, anular ou revogar, total o parcialmente a decisão
    recorrida.
                                                                                                                                                                       1ª VIA




Documento
Documentoassinado
             assinadodigitalmente.
                        digitalmente por Carlos Eduardo Carvalho Lima, em 27/12/2018 às 18:52
Consulte a autenticidade deste documento em http://sicnet2.aneel.gov.br/sicnetweb/v.aspx, informando o código de verificação 4BC7F9C0004A0CF8
```

**After** (`auto-infracao-48500.004024-2017-80.md`, same page, everything
above `1ª VIA` copied character for character — note "NOME:", "CARGO/FUNÇÃO:"
and "ASSINATURA:" are the form's own field labels and stay, since they are
main content, not the actual signature stamp):

```
    7. REPRESENTANTE DO ÓRGÃO FISCALIZADOR

    NOME:                                Carlos Eduardo Carvalho Lima

    CARGO/FUNÇÃO:                        Superintendente Adjunto                           MATRÍCULA nº                     2549785

    ASSINATURA:

    Conforme art 34 da resolução normativa ANEEL n°63 de 12 de maio de 2004, o recurso deverá ser dirigido a autoridade que proferiu a decisão, acima identificada, a qual, se
    não a reconsiderar, no prazo de 5 (cinco) dias, o encaminhará a diretoria da ANEEL, que poderá confirmar, modificar, anular ou revogar, total o parcialmente a decisão
    recorrida.
                                                                                                                                                                       1ª VIA
```

The garbled `Documento / Documentoassinado / assinadodigitalmente. /
digitalmente por Carlos Eduardo Carvalho Lima, em 27/12/2018 às 18:52` +
`Consulte a autenticidade ...` block — a rotated ICP/SICNET signature stamp
that `pdftotext -layout` merges with the running footer text — is gone; the
rest of the page, including the "NOME:"/"CARGO/FUNÇÃO:"/"ASSINATURA:" field
labels that are part of the official form itself, is untouched.

Across the full 57-page document, the `Exposição de Motivos` (the reasoning
body that the Auto de Infração itself says "passa a ser parte integrante do
presente Auto de Infração", page 2 onward) is kept in full — it is main
content even though SICNET's own internal numbering labels it as
`(ANEXO: 001)` in the page's corner stamp; that corner stamp is itself
removed as page-margin boilerplate, not treated as a reason to drop the
section it decorates. See `## Where the AC's line lives (contrato social /
attachments)` below.

## Where the AC's line lives (contrato social / attachments vs. main content)

Every one of the 10 PDFs is stamped by SICNET/SEI as `(ANEXO: NNN)` in its
corner — that is the source system's generic word for "an attached file in
this process", not the D14/issue #59 sense of "anexo" (a full separate
support document like a vistoria report or a laudo técnico). The
`Exposição de Motivos para o Auto de Infração` in every auto de infração PDF,
and the `ANEXO I – RAZÕES DA RECORRENTE` in `recurso-48500.009907-2025-96.pdf`,
are both labelled this way by the filing system while being exactly the main
legal reasoning the document exists to make — both are kept in full,
verbatim.

## Running for the whole `case-1-carolina-mmgd/` corpus

All 10 PDFs were processed this way; each `.md` sits next to its source PDF
(same directory, same basename, `.md` extension), ready to be the input for
the structural chunking of issues #60/#61:

| PDF | Pages | `.md` |
| --- | ---: | --- |
| `48500.004024-2017-80/auto-infracao-48500.004024-2017-80.pdf` | 57 | ✅ |
| `48500.004024-2017-80/recurso-48500.004024-2017-80.pdf` | 71 | ✅ |
| `48500.004024-2017-80/voto-48500.004024-2017-80.pdf` | 24 | ✅ |
| `48500.000639-2019-07/auto-infracao-48500.000639-2019-07.pdf` | 40 | ✅ |
| `48500.000639-2019-07/recurso-48500.000639-2019-07.pdf` | 26 | ✅ |
| `48500.000639-2019-07/voto-48500.000639-2019-07.pdf` | 15 | ✅ |
| `48500.901433-2024-53/auto-infracao-48500.901433-2024-53.pdf` | 11 | ✅ |
| `48500.901433-2024-53/voto-48500.901433-2024-53.pdf` | 15 | ✅ |
| `48500.009907-2025-96/recurso-48500.009907-2025-96.pdf` | 27 | ✅ |
| `48500.017555-2025-42/complementacao-recurso-48500.017555-2025-42.pdf` | 5 | ✅ |

The intermediate raw-text files (step 1's output) are scratch data and live
under `hackathon/.prototype-downloads/pdf-to-markdown/` (gitignored), same
convention as `document_downloader`.

## Verification performed

- Full-corpus `grep` sweep for signature/certification vocabulary
  (`assinad`, `autenticidade`, `código verificador`, `CRC`, `(Assinatura`,
  `(Assinado`) across all 10 generated `.md` files: the only remaining hits
  are legitimate content that happens to contain the word "assinado" in a
  sentence (e.g. "tem assinado com a ENEL... Contrato de Uso do Sistema de
  Distribuição", "CUSD assinado", "foi assinado pelo MME novo Termo de
  Compromisso") — not leftover signature blocks.
- Page-count integrity: `filter_verbatim.py` reports `pages kept: N / N` for
  all 10 documents — no page was ever dropped whole (`drop_pages` was empty
  for all 10, matching the finding above that none of them embeds a full
  separate attachment).
- Spot-checked that footnote-style document-number references (e.g. in
  `auto-infracao-48500.901433-2024-53.md`'s closing footnotes, or
  `voto-48500.901433-2024-53.md`'s citations to `Documento SEI nº ...`) were
  **not** caught by the page-margin stamp rule, since that rule only fires on
  a page's first non-blank line.
- Manually reviewed the highest-deletion-ratio document
  (`recurso-48500.004024-2017-80.md`, ~48% fewer lines than the raw
  extraction) to confirm the reduction is boilerplate/blank-line collapsing,
  not lost content — several of its pages (15–23) are almost empty because
  the source PDF pages are photographs of meter installations with only a
  one-line caption (`N - UC NNNNNNN`); `pdftotext` cannot extract text from
  an image, so there is nothing to preserve there.

## Known limitation

Page 24 of `recurso-48500.000639-2019-07.pdf` has visibly degraded text
extraction — different, inconsistent character substitutions than the rest
of the document (e.g. `Av B irb tc e u »` for what is `Av. Barbacena` on
every other page), which is characteristic of a scanned/re-photocopied
insert rather than a native PDF text layer. The signature line and two
garbled letterhead-footer lines on that page were still removed, by exact
literal match against this specific `pdftotext` output (still deterministic
and auditable — see `specs/recurso-48500.000639-2019-07.json`), but the
"verbatim" guarantee on that one page is only as good as `pdftotext`'s own
(degraded) reading of it; the agent did not attempt to guess or reconstruct
the intended words, since that would cross into paraphrase.
