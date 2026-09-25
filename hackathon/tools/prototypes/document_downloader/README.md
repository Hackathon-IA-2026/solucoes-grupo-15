# PROTOTYPE - document family downloader

This is a terminal prototype for the CapiWatt Lens document downloader.

It intentionally starts with two safe inputs:

- a manifest-driven flow for documents that are already known;
- a saved/exported SEI/Sicnet process page.

The public SEI/ANEEL and Sicnet pages may require captcha/challenge. This
prototype does not bypass that. When a captcha appears, open the page normally,
export/copy the process page, and feed that file to `discover_official_page.py`.

The goal is to validate the operational model:

1. start from a small list of known documents;
2. filter by process, source system, document type, family, or free text;
3. group several concrete PDFs as versions of the same document family;
4. copy/download the selected PDFs to a clean output directory;
5. emit a manifest and a Markdown timeline that the backend can later ingest.

The future SEI/Sicnet browser/API adapters should produce the same manifest
shape used here.

## Family rule

For this downloader prototype, the default is Carolina's operational meaning:
one process is one collection family, and the protocols/documents listed inside
that process are pieces of the family.

The parser still has `--family-mode protocol` for comparison, but
`--family-mode process` is the default and should be used for the assisted
downloader. The backend may later split this into a process node plus finer
document-version families; the downloader keeps enough metadata for that.

## Run

From the repository root:

```powershell
python hackathon/tools/prototypes/document_downloader/download_families.py `
  --manifest hackathon/tools/prototypes/document_downloader/sample_manifest.json `
  --out hackathon/.prototype-downloads/families
```

Dry-run only:

```powershell
python hackathon/tools/prototypes/document_downloader/download_families.py `
  --manifest hackathon/tools/prototypes/document_downloader/sample_manifest.json `
  --dry-run
```

Examples with filters:

```powershell
python hackathon/tools/prototypes/document_downloader/download_families.py `
  --manifest hackathon/tools/prototypes/document_downloader/sample_manifest.json `
  --type voto --dry-run

python hackathon/tools/prototypes/document_downloader/download_families.py `
  --manifest hackathon/tools/prototypes/document_downloader/sample_manifest.json `
  --process 48500.901433/2024-53 --dry-run

python hackathon/tools/prototypes/document_downloader/download_families.py `
  --manifest hackathon/tools/prototypes/document_downloader/sample_manifest.json `
  --query coelba --dry-run
```

## Discover from a saved official page

Generate a manifest from a copied/exported SEI page:

```powershell
python hackathon/tools/prototypes/document_downloader/discover_official_page.py `
  --input hackathon/tools/prototypes/document_downloader/samples/sei-process-48500.027542-2026-62.md `
  --out hackathon/.prototype-downloads/sei-48500.027542-2026-62-manifest.json `
  --source-system sei `
  --family-mode process
```

Then run the downloader on that generated manifest:

```powershell
python hackathon/tools/prototypes/document_downloader/download_families.py `
  --manifest hackathon/.prototype-downloads/sei-48500.027542-2026-62-manifest.json `
  --out hackathon/.prototype-downloads/sei-48500.027542-2026-62
```

## Assisted process flow

The assisted command opens SEI/Sicnet in the browser and waits while a person
passes captcha and saves/copies the final process page:

```powershell
python hackathon/tools/prototypes/document_downloader/assisted_process_downloader.py `
  --source-system sei `
  --page hackathon/tools/prototypes/document_downloader/samples/sei-process-48500.027542-2026-62.md `
  --out hackathon/.prototype-downloads/assisted-sei-48500.027542-2026-62 `
  --no-open-browser
```

Remove `--no-open-browser` to open the official search page. When captcha
appears, solve it manually, save/copy the process page to the path passed in
`--page`, then press Enter in the terminal.

## Assisted batch by filter

Use this when you want the first N process families from a theme/date filter.
The command opens the official search page, tells you which filter to apply, then
reads the saved results page and asks for each selected process page.

Offline sample:

```powershell
python hackathon/tools/prototypes/document_downloader/baixar_lote_assistido.py `
  --source-system sei `
  --theme "Fiscalizacao da Distribuicao: Processo Administrativo Sancionador" `
  --date-from 05/08/2026 `
  --date-to 05/08/2026 `
  --limit-families 3 `
  --results-page hackathon/tools/prototypes/document_downloader/samples/sei-results-august-05.md `
  --pages-dir hackathon/tools/prototypes/document_downloader/samples/process-pages `
  --out hackathon/.prototype-downloads/lote-agosto-05 `
  --no-open-browser
```

Real assisted run:

```powershell
python hackathon/tools/prototypes/document_downloader/baixar_lote_assistido.py `
  --source-system sei `
  --theme "Fiscalização da Distribuição: Processo Administrativo Sancionador" `
  --date-from 05/08/2026 `
  --date-to 05/08/2026 `
  --limit-families 3 `
  --results-page hackathon/.prototype-downloads/resultados-sei-agosto-05.html `
  --pages-dir hackathon/.prototype-downloads/paginas-processos-agosto-05 `
  --out hackathon/.prototype-downloads/lote-agosto-05
```

For the real run, solve captcha in the browser, save/copy the search results to
`--results-page`, then press Enter. If a selected process page is missing in
`--pages-dir`, the command tells you the exact filename to save before continuing.

## Notes

- Output is scratch data. It belongs under `hackathon/.prototype-downloads/`.
- Local files are copied; HTTP(S) locators are downloaded with standard library
  urllib.
- Restricted or unavailable files are recorded in the output manifest. If the
  official page has only metadata and no link, the item is marked
  `metadata_only` instead of inventing a PDF.
