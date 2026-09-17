---
name: research-vault-ingest-orchestrator
description: "Orchestrate the verified ResearchVault ingest of specified Zotero papers through identity, Fulltext, template-v2 Analytical Note, Knowledge decision, validation, and append-only logging."
---

# ResearchVault Ingest Orchestrator

Use this control plane only when the user identifies paper(s) to ingest or asks for their ingest state. It does not discover papers or duplicate specialist work.

## Configuration and specialists

Resolve the Vault through `RESEARCH_VAULT_ROOT` or the current workspace. Read the current instructions for:

1. `zotero-data-fetcher`
2. `zotero-fulltext-archiver`
3. `zotero-analytical-writer`
4. `research-vault-knowledge-maintainer`

`research-vault-literature-retrieval` supports later questions; `zotero-collection-manager` schedules a specified batch.

## Pipeline

Read [references/ingest-gates.md](references/ingest-gates.md), [references/pipeline.md](references/pipeline.md), [references/workflow-states.md](references/workflow-states.md), and [references/validation-contract.md](references/validation-contract.md).

```text
SPECIFIED PAPER
  -> STATE INSPECTION
  -> ZOTERO IDENTITY
  -> FULLTEXT GATE
  -> ANALYTICAL NOTE GATE
  -> NOTE/FULLTEXT PAIR VALIDATION
  -> KNOWLEDGE INGEST DECISION
  -> KNOWLEDGE UPDATE OR NO_KNOWLEDGE_CHANGE
  -> FINAL VALIDATION
  -> APPEND-ONLY LOG
```

Stop downstream writes when a gate fails. Partial work remains retryable and must not be labelled complete.

## Modes

- `NORMAL_INGEST` is the default and includes identity, pairing, Knowledge links/sidecars, statement-drift checks, validator exit code, and append-only log.
- `ACCEPTANCE_TEST` is used only when the user explicitly requests a Skill/system/retrieval acceptance test.

## Minimal action

- Valid Note + Fulltext + Knowledge decision + validation: `ALREADY_COMPLETE`.
- Valid artifacts but historical Note explicitly selected for v2 restructuring: repair that Note in place, preserve identity/evidence, then revalidate.
- Note only: run Fulltext and pairing gates.
- Fulltext only: run the writer and pairing gates.
- Valid pair without Knowledge decision: run only the decision.
- Missing artifacts: run only the necessary stages in order.

`NO_KNOWLEDGE_CHANGE` is a successful decision, not a skipped stage.

## Evidence and placement rules

- Parent `zotero_key` is the stable identity; `pdf_key` identifies the attachment.
- Place Note and Fulltext in the same leaf Collection.
- Canonical Fulltext is `03fulltext/<leaf-collection>/<zotero_key>.md`, with resolved images and `MISSING_IMAGES = 0`.
- New Notes use the current template v2 and writing specification. Do not batch-migrate historical Notes.
- Knowledge decisions parse the Note, then verify exact mechanisms/results/qualifiers in linked Fulltext or PDF. Missing Fulltext permits `note_supported`/deferred states only.
- Before Knowledge writes, read the matching template under `模板/知识库模板/`; update an existing canonical page before creating a synonym.

## Completion

Run the applicable Vault audit and ingest validator. After all required checks pass, append one human-readable Chinese event to `01knowledge/log.md` containing date, paper, Fulltext status, Note status, Knowledge action, updated pages/claims, and validation result. Do not rewrite log history or expose raw keys in human-facing log prose.
