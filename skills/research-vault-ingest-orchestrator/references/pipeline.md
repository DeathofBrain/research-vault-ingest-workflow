# 单篇 Ingest 流水线

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

## 执行规则

- 每个 gate 失败即停止下游写入，记录可重试或待人工状态，不得把部分结果标记为成功。
- 各阶段只调用对应专业 Skill，不在此处重写全文或中文笔记。
- 默认 `NORMAL_INGEST`；仅当用户明确要求测试/验收时才启用 `ACCEPTANCE_TEST`。
- 安全校验在 `NORMAL_INGEST` 中始终保留：身份、Note/Fulltext 配对、Knowledge 链接、claim sidecar、陈述漂移检查、Knowledge validator 退出码。
