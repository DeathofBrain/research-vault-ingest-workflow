# Knowledge 冻结 Schema（可移植版）

本文件是 `research-vault-knowledge-maintainer` 的机器契约。除经 `SCHEMA_REVIEW_REQUIRED` 流程外，不得修改字段、枚举、ID 或元数据位置。

## 页面类型（仅此六类）

`knowledge-theme`、`knowledge-concept`、`knowledge-method`、`knowledge-relation`、`knowledge-controversy`、`knowledge-synthesis`

## 页面必备 frontmatter

所有页面必须包含：

```yaml
type: <上述六类之一>
title: "..."
aliases: []
status: emerging            # emerging / developing / established / conditional / contested
evidence_count: 0           # 等于 source_notes 中不重复 Analytical Note 的数量
source_notes: []            # 真实存在的 Note 相对路径
related: []
last_updated: "YYYY-MM-DD"
evidence_status: note_supported  # fulltext_verified / note_supported / interpretation / mixed
```

`knowledge-relation` 额外必填：`subject`、`relation`、`object`、`agreement`。

`agreement` 取值：`strong`、`mixed`、`conflicting`、`insufficient`。

`supporting_papers` 不是用户可见属性；机器身份统一通过 `source_notes` → Note 的 `zotero_key` → `fulltext_path` 解析。

## 证据角色（Evidence Role）

`直接证据`、`机制证据`、`情境证据`、`条件证据`、`相关证据`

## 验证状态（Verification State）

- `fulltext_verified`：已通过该 claim 所链接 Note 的 `fulltext_path` 定向核验原文。
- `note_supported`：由 Analytical Note 支撑，但未在 Fulltext 中逐条核验。
- `interpretation`：明确标注的跨论文综合推断，不是作者级发现。

页面级 `evidence_status` 只是粗粒度汇总，可为 `mixed`。

## Gap 来源（Gap Provenance）

- **Evidence-backed Gap**：严格限定于当前 Vault 覆盖范围内可见的空白。
- **Interpretive Gap**：研究机会类表述，必须标注 `interpretation`，不得陈述为全文献层面的绝对结论。

## 机器元数据位置

- Claims：`01knowledge/.meta/claims/`
- Gaps：`01knowledge/.meta/gaps/`
- 索引与机器报表：`01knowledge/.meta/`

Claim ID 格式：`claim-<页面slug>-<三位序号>`（如 `claim-urban-morphology-001`）。
Gap ID 格式：`gap-<页面slug>-<三位序号>`。

机器元数据不得以可见 prose、HTML 注释或 Obsidian 注释形式出现在用户可见 Knowledge Markdown 中。

## 正式 Knowledge Page 判定

仅当文件位于 `01knowledge/.meta/` 之外、处于人读 Knowledge 树中，且 frontmatter `type` 属于上述六类之一，才是正式 Knowledge Page。`index.md` 与 `log.md` 是导航例外。`.meta/**` 下的机器报表与 sidecar 一律不作为 Knowledge Page 参与校验。
