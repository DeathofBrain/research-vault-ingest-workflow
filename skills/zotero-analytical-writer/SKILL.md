---
name: zotero-analytical-writer
description: "Create or minimally update a Chinese ResearchVault Analytical Note from verified Zotero metadata and Fulltext, using the current template v2, exactly six mentor questions, and traceable evidence."
---

# Zotero Analytical Writer

## Authorities

Before writing, read both:

- `${RESEARCH_VAULT_ROOT}/模板/论文精读模板.md`
- `${RESEARCH_VAULT_ROOT}/模板/精读笔记写作规范.md`

For new Notes use `template_version: 2`. Do not migrate historical v1 Notes unless the user explicitly names the paper for restructuring.

## Stable identity and placement

- `zotero_key` is the paper identity; `pdf_key` identifies the PDF attachment.
- Store the Note at `02vault/论文库/<leaf-collection>/<title>.md`.
- Store `note_path` as `论文库/<leaf-collection>/<title>.md` and `fulltext_path` as `03fulltext/<leaf-collection>/<zotero_key>.md`.
- The Note and Fulltext must share the same leaf Collection. Preserve verified identity, paths, created date, formulas, and evidence when updating in place. Never create a duplicate Note to repair structure.

## Template v2 contract

The visible body follows this single line of argument:

`阅读总览 → 基本信息 → 导师六问（恰好六项） → 我的判断与研究启发 → 关联精读笔记 → 原文证据与核验记录`

- Each question starts with a direct answer, then expands.
- Question 4 explains the overall architecture or argument flow.
- Question 5 explains mechanisms, innovation, and trade-offs; select the actual number of technical points instead of forcing three.
- Question 6 evaluates the evidence appropriate to the paper type.
- Do not recreate parallel sections for research object, methods, mechanisms, data, and conclusions.

## Evidence discipline

- Fulltext/PDF is evidence; the Note is an interpretation layer.
- Do not generate an English quotation from a Chinese summary.
- Use PDF physical page numbers only after direct verification or a reliable mapping.
- Put short verbatim English quotations in the final evidence section, each preceded by a Chinese interpretation and followed by a verification record.
- The main text should cite PDF pages, figures/tables, or evidence IDs. Figures may directly support numeric findings.
- If evidence cannot be located, write `未在当前材料中定位到可核验原文` and keep the uncertainty.
- Terms are explained in Chinese only when they block understanding, normally 1–2 sentences. Mark paper paraphrase with `（论文释义；论文表述见 PDF 第 N 页）` and general knowledge with `（补充背景，非论文原文）`.

## Quality and indexing

- Explain mechanisms as input → processing/state → output → cost/trade-off.
- Distinguish author findings, empirical results, and the writer's interpretation.
- Embed only useful original figures near the claim/mechanism they support; include figure number, PDF page, Chinese reading guide, and evidence boundary.
- Link only real related Notes.
- Refresh the four indexes only for a new Note or when title/path/index fields change.
- After any write, run the Vault audit and ingest validator required by `AGENTS.md`; append the human-readable log only after validation passes.
