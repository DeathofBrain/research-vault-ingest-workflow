# Ingest Gates

## 各 gate 通过条件

1. **STATE INSPECTION**：读取现有日志与 Note/Fulltext 状态，判定 `ALREADY_COMPLETE` 或需要执行的阶段。
2. **ZOTERO IDENTITY**：解析 `zotero_key` 与 `pdf_key`，不做基于标题的模糊磁盘搜索作为身份依据。
3. **FULLTEXT GATE**：正式 Fulltext 为 `03fulltext/<collection>/<zotero_key>.md`，图片链接已解析且 `MISSING_IMAGES = 0`。缺失时若本机未装 MinerU，标记 `MINERU_FAILED` / `FULLTEXT_DEFERRED`。
4. **ANALYTICAL NOTE GATE**：按 `论文精读模板.md` 创建或模板修复 Note，保留稳定身份与路径。
5. **PAIR VALIDATION**：Note↔Fulltext 双向入口与路径一致；结论条目“主要发现 + 原文引用”成对。
6. **KNOWLEDGE INGEST DECISION**：两层证据通过（Note 结构化字段 + 原文核验），决定更新或 `NO_KNOWLEDGE_CHANGE`。
7. **FINAL VALIDATION**：validator 与模板/覆盖审计通过。
8. **APPEND-ONLY LOG**：向 `01knowledge/log.md` 追加中文事件，不重写历史。

## 最小行动决策表

| 观测状态 | 必需动作 |
| --- | --- |
| Note/Fulltext/Knowledge 均有效且 Note 符合模板 | `ALREADY_COMPLETE`，不重处理 |
| Note 与 Fulltext 有效，但 Note 不符合模板 | 仅模板修复，同一路径，再校验 |
| 有 Note 缺 Fulltext | 仅 Fulltext gate |
| 有 Fulltext 缺 Note | 仅 Analytical Note gate |
| Note/Fulltext 有效但 Knowledge 未纳入 | 仅 Knowledge 决策 |
| 必备产物缺失 | 按序执行所需阶段 |
