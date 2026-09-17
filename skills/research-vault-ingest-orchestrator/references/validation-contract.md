# 验证契约（Validation Contract）

## 必须通过

- 身份：`zotero_key` / `pdf_key` 解析成功且与 Zotero 数据库一致。
- Note/Fulltext 配对：双向入口与路径一致，无幽灵链接。
- Knowledge 链接：`source_notes` 全部指向真实 Analytical Note。
- Claim sidecar：`01knowledge/.meta/claims/` 与页面 claim 一一对应（若适用）。
- 陈述漂移检查：Note 与 Fulltext 表述一致，无反向生成引语。
- Knowledge validator 退出码为 0。
- 模板/覆盖审计：页面使用当前模板结构；覆盖账本无未解释遗漏。

## 禁止

- 不得凭摘要反向生成英文 quote。
- 不得在 Fulltext 缺失时编造页码或引语。
- 不得把 `note_supported` 记为 `fulltext_verified`。
- 不得仅因“已有笔记”而跳过 Fulltext 或 Knowledge 覆盖。

## 完成定义

所有适用校验通过后，向 `01knowledge/log.md` 追加一条中文事件，包含日期、文献名、Fulltext 状态、Note 状态、Knowledge 动作、更新页面/claims 与校验结果。`NORMAL_INGEST` 不运行验收套件（硬检索测试、跨主题检索、自主主题测试、扩展审计报告），除非用户明确要求。
