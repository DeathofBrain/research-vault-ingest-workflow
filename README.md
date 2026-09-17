# ResearchVault Ingest Workflow

一个可移植的 **Zotero → MinerU Fulltext → 中文精读笔记 → 跨论文 Knowledge → 校验与日志** 工作流仓库。

本仓库整理了当前 ResearchVault 使用的 Codex skills、模板、校验工具和多终端协作约定。它**不包含** Zotero 数据库、论文 PDF、MinerU 全文、现有精读笔记、知识库内容或 API key。

## 包含内容

- `skills/`：单篇入库控制器及 6 个专业 skill
  - `research-vault-ingest-orchestrator`
  - `zotero-data-fetcher`
  - `zotero-fulltext-archiver`
  - `zotero-analytical-writer`
  - `research-vault-knowledge-maintainer`
  - `research-vault-literature-retrieval`
  - `zotero-collection-manager`
- `vault-kit/tools/`：Zotero 只读提取、MinerU 运行器、入库校验器和审计套件
- `vault-kit/模板/`：精读模板 v2、写作规范和 Knowledge 页面模板
- `scripts/bootstrap.py`：将工具/模板安装到实际 Vault，并将 skills 安装或链接到 Codex
- `scripts/doctor.py`：检查路径、Zotero、MinerU、Python 依赖和 skills
- `docs/multi-terminal.md`：使用 Git worktree 让多个终端并行处理不同论文

## 快速开始

macOS / Linux：

```zsh
git clone <本仓库地址>
cd research-vault-ingest-workflow
python3 -m pip install -r requirements.txt

# 安装到现有 Vault；默认不覆盖已有文件
python3 scripts/bootstrap.py \
  --vault "$HOME/Documents/ResearchVault" \
  --install-skills --skill-mode symlink

export RESEARCH_VAULT_ROOT="$HOME/Documents/ResearchVault"
export ZOTERO_DATA_DIR="$HOME/Zotero"
python3 scripts/doctor.py --vault "$RESEARCH_VAULT_ROOT"
```

Windows PowerShell：

```powershell
git clone <本仓库地址>
Set-Location research-vault-ingest-workflow
python -m pip install -r requirements.txt
python scripts/bootstrap.py `
  --vault "$HOME\Documents\ResearchVault" `
  --install-skills --skill-mode copy
python scripts/doctor.py --vault "$HOME\Documents\ResearchVault"
```

Windows 默认推荐 `--skill-mode copy`，不依赖目录符号链接权限。doctor 会在 Zotero 正在运行、
数据库处于 WAL 模式时创建临时只读快照，并校验配置的 MinerU 命令确实可执行。

如果 Vault 尚无 `AGENTS.md`，bootstrap 会从 `AGENTS.example.md` 创建；已有文件绝不默认覆盖。

## 配置

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `RESEARCH_VAULT_ROOT` | 当前 Vault / 工具所在 Vault | 实际 ResearchVault 根目录 |
| `ZOTERO_DATA_DIR` | `~/Zotero` | Zotero 数据目录 |
| `ZOTERO_DB` | `$ZOTERO_DATA_DIR/zotero.sqlite` | Zotero SQLite 路径 |
| `ZOTERO_STORAGE` | `$ZOTERO_DATA_DIR/storage` | Zotero 附件根目录 |
| `MINERU_BIN` | `PATH` / `CONDA_PREFIX` 自动查找 | MinerU 可执行文件 |
| `MINERU_BACKEND` | `pipeline` | MinerU 后端 |
| `MINERU_TIER` | 按 backend 映射（`pipeline` → `basic`） | MinerU 4 解析档位 |
| `CODEX_HOME` | `~/.codex` | Codex skills 安装目录 |
| `RESEARCH_VAULT_AUDIT_EXCEPTIONS` | `<vault>/config/audit_exceptions.json` | 无文本层页等审计例外 |

可复制 `config/research-vault.env.example` 到自己的 shell 配置。不要把本机绝对路径、token 或 API key 提交到仓库。

MinerU 4 推荐将 `MINERU_BIN` 指向 `mineru-kit`（Windows 为 `mineru-kit.exe`）；运行器会使用
`mineru-kit parse`。旧版 `mineru` 命令仍受支持，因此现有 macOS 配置不需要迁移。

## 单篇入库

1. 通过父条目 `zotero_key` 解析身份和 PDF 附件。
2. 复用或生成 `03fulltext/<叶子Collection>/<zotero_key>.md`，要求图片链接全部有效。
3. 按模板 v2 写入/更新同一叶子 Collection 下的中文精读笔记。
4. 校验 Note ↔ Fulltext、原文引文、索引和 Knowledge sidecars。
5. 做 Knowledge 更新或记录 `NO_KNOWLEDGE_CHANGE`。
6. 全部校验通过后，向 `01knowledge/log.md` 追加人读事件。

详细 gate 见 `skills/research-vault-ingest-orchestrator/references/`。

## 多终端处理

不要让多个终端直接同时写同一个工作树。对实际 **Vault Git 仓库** 使用“一篇论文一个 branch + worktree”：

```zsh
cd "$RESEARCH_VAULT_ROOT"
git worktree add ../rv-ABCD1234 -b ingest/ABCD1234 main
```

各终端可以并行写自己的论文 Note、Fulltext、图片和运行记录；四个索引、Knowledge 索引/sidecar 索引及 `01knowledge/log.md` 在合并阶段串行更新。完整策略见 [docs/multi-terminal.md](docs/multi-terminal.md)。

## 更新安装

```zsh
git pull
python3 scripts/bootstrap.py \
  --vault "$RESEARCH_VAULT_ROOT" \
  --install-skills --skill-mode symlink --force
```

`--force` 覆盖前会把原文件备份到 `<vault>/.research-vault-workflow-backups/<timestamp>/`，不会删除额外文件。

## 验证仓库

```zsh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py --vault "$RESEARCH_VAULT_ROOT"
```

在实际 Vault 修改笔记/索引后：

```zsh
python3 "$RESEARCH_VAULT_ROOT/tools/audit/run_all.py"
python3 "$RESEARCH_VAULT_ROOT/tools/validate_ingest.py" \
  --note '02vault/论文库/<collection>/<paper>.md' \
  --pdf '/absolute/path/to/paper.pdf'
```
