# 多终端并行入库

## 原则

- 并行单位是论文，不是共享索引文件。
- 每篇论文使用独立 Git branch 与 worktree，避免多个终端覆盖同一工作树。
- 原始 PDF 和 Zotero 数据库留在本机外部位置，不进入 Git。
- `zotero_key` 是任务分配与分支命名的稳定身份。

## 推荐流程

假设实际 Vault 本身是 Git 仓库：

```zsh
cd "$RESEARCH_VAULT_ROOT"
git fetch --all --prune

git worktree add ../rv-ABCD1234 -b ingest/ABCD1234 main
git worktree add ../rv-WXYZ5678 -b ingest/WXYZ5678 main
```

终端 A：

```zsh
export RESEARCH_VAULT_ROOT="$(cd ../rv-ABCD1234 && pwd)"
cd "$RESEARCH_VAULT_ROOT"
# 只处理 ABCD1234
```

终端 B 同理只处理另一个 key。

## 可以并行写的内容

- 该论文自己的 `02vault/论文库/<collection>/<title>.md`
- 该论文自己的 `03fulltext/<collection>/<zotero_key>.md`
- `images/<zotero_key>/` 与 `_runs/<zotero_key>/`
- 该论文独立的阶段状态或运行记录

## 需要串行集成的内容

这些文件冲突概率高，应在合并论文分支后由一个集成终端统一更新和校验：

- `02vault/_index/` 下四个索引
- `01knowledge/index.md`
- `01knowledge/.meta/claims_index.json`
- `01knowledge/.meta/gaps_index.json`
- `01knowledge/.meta/validation_report.json`
- `01knowledge/log.md`
- 跨论文 Knowledge Page 及其 claim/gap sidecars

## 分支提交建议

论文分支先提交论文私有产物：

```zsh
git add -- '02vault/论文库/...' '03fulltext/...'
git commit -m 'feat(ingest): add ABCD1234 analytical note and fulltext'
```

集成终端逐个合并，然后统一刷新共享索引、Knowledge 和日志：

```zsh
git switch main
git merge --no-ff ingest/ABCD1234
git merge --no-ff ingest/WXYZ5678
python3 tools/audit/run_all.py
git add 02vault/_index 01knowledge
git commit -m 'chore(vault): reconcile indexes knowledge and ingest log'
```

如果某论文分支已经写了共享文件，不要用 `ours/theirs` 粗暴覆盖；保留两边论文事实，重新生成/人工合并共享索引，并保持 `log.md` append-only。

## 同一台机器上的 Codex skills

每个 worktree 都设置自己的 `RESEARCH_VAULT_ROOT`。skills 可以统一 symlink 到本 workflow 仓库，不需要在每个 worktree 复制一份。

## 多台机器

- 每台机器 clone workflow 仓库并运行 bootstrap。
- 每台机器单独设置 Zotero 与 MinerU 路径；不要提交本机 `.env`。
- 只有具备原始 PDF 的机器才能把 claim 标成 `fulltext_verified`。
- 合并前先 rebase/merge 最新主分支并重新跑校验。
