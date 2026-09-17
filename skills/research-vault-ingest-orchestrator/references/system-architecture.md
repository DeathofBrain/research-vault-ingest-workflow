# 系统架构（macOS 适配版）

## 组件

1. **zotero-data-fetcher**：解析 Zotero 身份（`zotero_key`、`pdf_key`），提取元数据、批注、全文缓存。
2. **zotero-fulltext-archiver**：获取或校验正式 Fulltext（依赖 MinerU；本机已安装于 conda 环境 `mineru`，运行器见 `run_mineru_production.py`）。
3. **zotero-analytical-writer**：生成/规范化单篇中文 Analytical Note。
4. **research-vault-knowledge-maintainer**：跨论文 Knowledge 决策与更新。
5. **research-vault-literature-retrieval**：后续证据问答（非 ingest 阶段）。

`zotero-collection-manager` 是兼容的批量/小批量调度器。

## 目录布局

- Knowledge Wiki：`${RESEARCH_VAULT_ROOT}/01knowledge`
- Analytical Notes：`${RESEARCH_VAULT_ROOT}/02vault`
- 正式 Fulltext：`${RESEARCH_VAULT_ROOT}/03fulltext`
- Knowledge 机器元数据：`${RESEARCH_VAULT_ROOT}/01knowledge/.meta`
- Knowledge 页面模板：`${RESEARCH_VAULT_ROOT}/模板/知识库模板`
- MinerU 运行器：`${RESEARCH_VAULT_ROOT}/tools/run_mineru_production.py`
- 精读模板：`${RESEARCH_VAULT_ROOT}/模板/论文精读模板.md`

## 稳定身份

- 主键：`zotero_key`（父条目）。
- 附件身份：`pdf_key`（PDF 附件条目 key）。
- 标题仅用于人读校验，不作为主键。
