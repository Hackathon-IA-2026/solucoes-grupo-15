# PROTOTYPE - document family downloader

This is a terminal prototype for the CapiWatt Lens document downloader.

It intentionally starts with a manifest-driven flow instead of scraping SEI or
Sicnet directly. The goal is to validate the operational model:

1. start from a small list of known documents;
2. filter by process, source system, document type, family, or free text;
3. group several concrete PDFs as versions of the same document family;
4. copy/download the selected PDFs to a clean output directory;
5. emit a manifest and a Markdown timeline that the backend can later ingest.

The future SEI/Sicnet adapters should produce the same manifest shape used here.

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

## Notes

- Output is scratch data. It belongs under `hackathon/.prototype-downloads/`.
- Local files are copied; HTTP(S) locators are downloaded with standard library
  urllib.
- Restricted or unavailable files are recorded in the output manifest as failed
  items instead of stopping the whole batch.

