# 综合页（Synthesis）成熟度门槛

`knowledge-theme` 的创建与 `knowledge-synthesis` 的创建是两个独立决策。

## 门槛条件

创建或实质性重构 Synthesis 页必须同时满足：

1. 存在多条稳定的跨论文 Relation 或 Claim（至少来自两篇以上已核验的 Analytical Note）；
2. 跨论文综合证据充分，不是单篇论文的扩展摘要；
3. 至少具备以下一项有实质价值的产出：条件、机制、边界、争议，或证据支撑的研究空白（Evidence-backed Gap）。

## 禁止事项

- 不得仅凭论文数量阈值自动创建 Synthesis 页（例如“满 N 篇就建综合”）。
- 不得在 Theme 创建时顺带自动创建 Synthesis 页。
- 不得用 Knowledge Page 作为另一科学 claim 的证据；Knowledge 是派生层。

## 校验

- 创建 Theme 时不触发 Synthesis 门槛检查；创建 Synthesis 时必须逐项核对上述条件并记录判断依据。
- 证据不足时保留 Theme/Relation 结构，报告 `SYNTHESIS_NOT_YET_MATURE` 而非强行建页。
