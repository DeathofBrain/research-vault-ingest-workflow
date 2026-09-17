---
name: zotero-data-fetcher
description: "Resolve Zotero parent-item and PDF attachment identities, then extract metadata, annotations, and cached text without modifying Zotero. Use at the identity/evidence-acquisition stage of a ResearchVault ingest."
---

# Zotero Data Fetcher

## Configuration

Resolve paths in this order:

1. `RESEARCH_VAULT_ROOT`; otherwise use the current Vault root.
2. `ZOTERO_DB`; otherwise `${ZOTERO_DATA_DIR:-~/Zotero}/zotero.sqlite`.
3. `ZOTERO_STORAGE`; otherwise `${ZOTERO_DATA_DIR:-~/Zotero}/storage`.

Use `${RESEARCH_VAULT_ROOT}/tools/extract_item_json.py`. The script opens Zotero SQLite read-only and copies WAL files to a temporary directory only when a direct read is blocked.

## Identity contract

- `zotero_key` is the parent item key and is the stable paper identity.
- `pdf_key` is the PDF attachment item key.
- A title is display-only. Title search may produce candidates, but must not replace key-based identity.
- Resolve the PDF path from Zotero SQLite. Do not assume the parent key equals the attachment storage directory.

## Evidence order

1. Zotero annotations and notes.
2. The attachment `.zotero-ft-cache`.
3. The original PDF when the first two are insufficient or a formula/page/quotation must be verified.

Return a raw evidence buffer in the source language. Do not translate, summarize, or write an Analytical Note in this stage.

## Commands

```zsh
python3 "$RESEARCH_VAULT_ROOT/tools/extract_item_json.py" --key <ZOTERO_KEY>
python3 "$RESEARCH_VAULT_ROOT/tools/extract_item_json.py" --title <keyword>
python3 "$RESEARCH_VAULT_ROOT/tools/extract_item_json.py" --collection <collection>
```
