# ResearchVault 工作区约定

本目录是 Zotero 论文精读与知识库。默认行为：

- 在普通问答中优先使用 `$research-vault-literature-retrieval`；先读 `02vault/_index/`，再定位精读笔记，必要时定向核验 `03fulltext/`。
- 证据不足时明确写 `Vault 中未找到足够依据`。
- 默认回答结构：`结论` → `支持文献` → `差异/争议` → `对我研究的启发`。
- 默认只读；只有用户明确要求时才修改笔记、索引、Knowledge 或 Zotero。

## 入库

- 指定论文的入库使用 `$research-vault-ingest-orchestrator`。
- 稳定身份是父条目 `zotero_key`；`pdf_key` 是 PDF 附件身份，标题仅用于人读校验。
- Note 与 Fulltext 一律归到最具体的叶子 Collection：
  - `02vault/论文库/<collection>/<title>.md`
  - `03fulltext/<collection>/<zotero_key>.md`
- 新笔记使用 `模板/论文精读模板.md` 的 `template_version: 2`，并先读 `模板/精读笔记写作规范.md`。
- 六问恰好六项；创新性归第五问；英文逐字引文集中到文末证据区。
- Fulltext 必须保持原始正文，不翻译、不总结；图片链接必须全部可解析。
- Knowledge 是派生层；精确主张须回到 Note 链接的 Fulltext/PDF 核验。
- 所有适用校验通过后才向 `01knowledge/log.md` 追加事件，日志不可重写历史。

## 多终端

- 一篇论文一个 Git branch/worktree。
- 论文私有产物可并行；四个全局索引、Knowledge 索引/sidecar 索引和 `01knowledge/log.md` 在集成时串行更新。
- 不提交 Zotero 数据库、原始 PDF、token、API key 或本机私密配置。
