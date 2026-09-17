# 知识库模板说明

本目录是 ResearchVault Knowledge 页面（人读层）的唯一结构权威。创建或实质性重构 Knowledge 页面前，必须先读本说明和对应的页面模板。

## 页面类型与模板

| 页面类型 | 模板文件 | 用途 |
| --- | --- | --- |
| `knowledge-theme` | `主题模板.md` | 持久研究主题 |
| `knowledge-concept` | `概念模板.md` | 核心概念/定义 |
| `knowledge-method` | `方法模板.md` | 反复出现的方法 |
| `knowledge-relation` | `关系模板.md` | 变量/概念之间的共享关系 |
| `knowledge-controversy` | `争议模板.md` | 真实争议 |
| `knowledge-synthesis` | `争议模板.md` 为参考，另见 `research-vault-knowledge-maintainer` 的合成成熟度门槛 | 跨论文综合 |

## 机器契约

冻结 schema 见 skill 内 `references/knowledge-schema.md`。页面模板负责可见结构，schema 负责机器字段；两者冲突时以 schema 为准并报告 `SCHEMA_REVIEW_REQUIRED`，不得自行新增字段。

## 通用可见结构（所有页面）

1. `> [!summary]` 一句话综合
2. 概述与边界
3. 证据总览表（论文 / 证据角色 / 验证状态 / 链接）
4. 分主题或分 claim 的发现区（含条件、机制、局限）
5. 研究空白
6. 使用与启示
7. 来源与边界（`source_notes` 真实路径链接）

## 语言

面向用户的标题、正文、证据描述、空白描述与导航一律中文优先；仅保留标准科技术语、符号与首次出现的中英双语术语。
