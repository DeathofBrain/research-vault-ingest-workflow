# Fulltext promotion checklist

- Parent `zotero_key` and attachment `pdf_key` were resolved from Zotero SQLite.
- Source PDF path exists and its SHA-256 was recorded.
- MinerU used an ASCII working copy whose SHA-256 matches the source.
- One explicit backend and one paper were used for the run.
- Canonical Markdown is `03fulltext/<leaf-collection>/<zotero_key>.md`.
- Images are under `03fulltext/<leaf-collection>/images/<zotero_key>/`.
- Every local image reference resolves (`MISSING_IMAGES = 0`).
- Run command, logs, backend, exit code, and artifact paths are retained under `_runs/<zotero_key>/`.
