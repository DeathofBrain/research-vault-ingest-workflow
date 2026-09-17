---
name: research-vault-literature-retrieval
description: "Use a ResearchVault workspace as the default evidence source: read indexes first, locate relevant Analytical Notes, selectively verify linked Fulltexts, and answer only from Vault evidence."
---

# ResearchVault Literature Retrieval

Resolve the Vault root from `RESEARCH_VAULT_ROOT`; otherwise use the current workspace containing `AGENTS.md`, `01knowledge`, `02vault`, and `03fulltext`.

## Retrieval order

1. Read, when present, `02vault/_index/文献索引.md`, `研究主题索引.md`, `研究方法索引.md`, and `字段补全检查.md` in that order.
2. Search `02vault/论文库/` using Chinese/English terms, method names, variables, places, titles, and aliases.
3. Open the most relevant 1–3 Analytical Notes completely.
4. For exact definitions, mechanisms, formulas, results, or quotations, follow each Note's `fulltext_path` and verify selectively in `03fulltext/` or the original PDF.
5. Answer only from the retrieved Vault evidence. If it is insufficient, state `Vault 中未找到足够依据` instead of filling gaps from memory.

## Default answer structure

1. `结论`
2. `支持文献`
3. `差异/争议`
4. `对我研究的启发`

Default to read-only. Modify Notes, indexes, `AGENTS.md`, or Zotero only when the user explicitly asks.
