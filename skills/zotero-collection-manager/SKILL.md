---
name: zotero-collection-manager
description: "Incrementally schedule the ResearchVault ingest pipeline for a specified Zotero Collection or small batch, with retryable per-paper states, resumability, and conflict-aware multi-terminal execution."
---

# Zotero Collection Manager

## Scope

Process only the Collection or papers named by the user. Default to a single paper or small batch. Use `zotero_key` as the identity and call the specialist skills in order:

`data-fetcher → fulltext-archiver → analytical-writer → pair validation → knowledge decision → final validation/log`

Do not rewrite Fulltext or Analytical Notes in the manager itself.

## Incremental state

Record at least `zotero_key`, title, leaf Collection, `pdf_found`, `fulltext`, `images_valid`, `note`, `linked`, `knowledge_decision`, timestamps, reason, and artifact paths. A file's existence alone is not completion.

States include `COMPLETE`, `PARTIAL_FULLTEXT_MISSING`, `PARTIAL_NOTE_MISSING`, `IMAGES_INVALID`, `PDF_NOT_FOUND`, `MINERU_FAILED`, `KEY_CONFLICT`, `FULLTEXT_DEFERRED`, `NO_KNOWLEDGE_CHANGE`, and user-confirmed `PERMANENTLY_IGNORED`.

## Resume rules

- Reuse successful stages after checking their invariants.
- A valid Note with missing Fulltext runs only the Fulltext gate and pairing updates.
- A valid Fulltext with missing Note runs only the writer gate.
- Valid Note/Fulltext with no Knowledge decision runs only that decision.
- Temporary failure is retryable; `跳过` is not a terminal state.

## Multi-terminal rule

Assign each paper to a separate Git branch/worktree. A paper worker may write its Note, Fulltext, images, and per-paper run record. Serialize shared writes to the four indexes, `01knowledge/index.md`, sidecar indexes, and append-only `01knowledge/log.md` during integration. See the repository `docs/multi-terminal.md`.
