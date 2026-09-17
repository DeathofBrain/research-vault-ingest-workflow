---
name: zotero-fulltext-archiver
description: "Convert or validate a Zotero PDF as canonical ResearchVault MinerU Markdown with resolved images, stable identity, reproducible logs, and no rewriting of source text. Use only for the Fulltext gate of an ingest."
---

# Zotero Fulltext Archiver

## Preconditions

- Resolve `zotero_key`, `pdf_key`, leaf Collection, and original PDF through `zotero-data-fetcher`.
- Reuse a valid existing Fulltext. Do not rerun MinerU merely because a Note is being updated.
- Work on one paper per MinerU process unless the user explicitly requests a controlled batch.

## Canonical output

- Markdown: `${RESEARCH_VAULT_ROOT}/03fulltext/<leaf-collection>/<zotero_key>.md`
- Images: `${RESEARCH_VAULT_ROOT}/03fulltext/<leaf-collection>/images/<zotero_key>/`
- Run records: `${RESEARCH_VAULT_ROOT}/03fulltext/<leaf-collection>/_runs/<zotero_key>/`

The note and Fulltext must use the same leaf Collection. Preserve extracted source-language body text; do not translate, summarize, or convert it into a Knowledge Page.

## Conversion

Use `${RESEARCH_VAULT_ROOT}/tools/run_mineru_production.py`. It creates an ASCII working copy, checks SHA-256 equality, invokes an explicit backend, and writes timestamped logs.

```zsh
python3 "$RESEARCH_VAULT_ROOT/tools/run_mineru_production.py"   <original.pdf> <staging-output-dir> --key <zotero_key> --backend pipeline
```

`MINERU_BIN` may point to the executable; otherwise the runner checks `PATH` and `CONDA_PREFIX`. `pipeline` is the conservative CPU default. Select another backend only when it is installed and appropriate for the terminal.

## Promotion gate

Before promoting staging output:

1. Identify MinerU's primary Markdown and image directory.
2. Copy/move them into the canonical paths without changing extracted prose.
3. Rewrite image links only as needed to point to `images/<zotero_key>/...`.
4. Verify every referenced local image exists; require `MISSING_IMAGES = 0`.
5. Record source PDF SHA-256, backend, command, start/end time, exit code, produced paths, and image count in the run directory.
6. Preserve failed staging/logs long enough to diagnose; do not mark the gate complete.

## Outcomes

- `FULLTEXT_VALID`: canonical Markdown exists, identity/path are correct, and all images resolve.
- `IMAGES_INVALID`: Markdown exists but one or more image links fail.
- `PDF_NOT_FOUND`: Zotero identity resolved but the attachment is unavailable.
- `MINERU_FAILED`: conversion exited non-zero or produced no usable Markdown.
- `FULLTEXT_DEFERRED`: the environment cannot currently run conversion; downstream evidence must not be labelled `fulltext_verified`.
