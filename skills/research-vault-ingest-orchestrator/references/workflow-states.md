# 工作流状态（Workflow States）

每篇论文按 Item Key 记录状态：

- `COMPLETE`：`pdf_found && fulltext && images_valid && note && linked` 全真。
- `PARTIAL_FULLTEXT_MISSING`：Note 存在，Fulltext 未建立。
- `PARTIAL_NOTE_MISSING`：Fulltext 存在，Note 未建立。
- `IMAGES_INVALID`：全文存在但图片缺失或引用错误。
- `PDF_NOT_FOUND`：找不到父条目 PDF，可重试。
- `MINERU_FAILED`：MinerU 解析失败，可重试。
- `KEY_CONFLICT`：主键或标题映射冲突，需人工确认。
- `PERMANENTLY_IGNORED`：仅用户明确确认永久忽略后使用。
- `FULLTEXT_DEFERRED`：Fulltext 暂缺，证据以 `note_supported` 表达。
- `NO_KNOWLEDGE_CHANGE`：Knowledge 决策成功但无需变更。
- `SCHEMA_REVIEW_REQUIRED`：证据无法用冻结 schema 表达时上报。

工作流状态不是 Knowledge 证据枚举，禁止写入冻结 Knowledge schema 字段。
