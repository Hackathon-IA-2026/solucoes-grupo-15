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

The safe default is conservative: one official protocol/document number is one
family. Several rows are grouped into one family only when the source exposes a
structured version/rectification relation or when a human curator confirms that
they are versions of the same piece.

That means a "recurso" and a "complementacao de recurso" are related documents,
not automatically versions of the same family.

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
  --source-system sei
```

Then run the downloader on that generated manifest:

```powershell
python hackathon/tools/prototypes/document_downloader/download_families.py `
  --manifest hackathon/.prototype-downloads/sei-48500.027542-2026-62-manifest.json `
  --out hackathon/.prototype-downloads/sei-48500.027542-2026-62
```

## Notes

- Output is scratch data. It belongs under `hackathon/.prototype-downloads/`.
- Local files are copied; HTTP(S) locators are downloaded with standard library
  urllib.
- Restricted or unavailable files are recorded in the output manifest. If the
  official page has only metadata and no link, the item is marked
  `metadata_only` instead of inventing a PDF.
