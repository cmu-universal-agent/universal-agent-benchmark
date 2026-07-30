# Stress Testing — 设计思路

Owner: Lanfang (hlf) · Branch: `lanfang/stress-testing-plan`

## 为什么要做 stress test

Benchmark 的目标不是看 agent「能不能答对常规题」，而是回答：

> 从**逻辑严谨**的医疗场景切到**创意/工具密集**的电商场景时，框架在哪一类压力下先崩？

`standard` case 测的是能力和准确率；stress case 测的是**边界、恢复力和一致性**——JSON 格式、工具权限、安全拒答、长上下文遗忘、重复运行漂移等。

## 核心设计原则

**一次只施加一种压力。** 每个 variant 相对 base case 只改一个因素（输入、工具环境、上下文长度、或运行协议）。这样失败可以归因到具体的 `stress_type`，而不是混成一团。

**base 不动，variant 另存。** Core pilot 的 60 个 case 是评测基准本身，不在原文件上打补丁。Stress 版本单独存放，通过 `stress_variant_of`（待 Chloe 确认）指回 base。

**结构失败和内容失败分开。** `adapter/evaluator.py` 管 JSON、schema、instruction 合规；gold/rubric 管答案对不对；`unsafe_response` 单独标记输出是否有害——三者不混为一个分数。

**stress 不是 benchmark 分数。** 在 pilot 正式签字之前，stress 结果只作基础设施/可靠性证据，不直接用来排名框架。

## 文档分工

| 文档 | 思路 |
|---|---|
| `stress_testing_strategy.md` | 八种 stress 各自测什么、控制变量是什么、工具/失败/长文本/安全/重复运行怎么设计 |
| `eight_core_stress_matrix.md` | 八个 task type 各选一个**最有代表性**的主 stress，写清「改了什么、该怎样、不能怎样、怎么判过/判挂」 |
| `stress_failure_rubric.md` | 所有 stress 共用一套失败模式词汇表和优先级，避免每个人各写各的 |
| `schema_field_review.md` §10 | Stress fixture 需要但尚未进 schema 的字段，先提案、后落地 |

## 和代码结构的关系

思路上的数据流：

```text
benchmark_case.schema.json     定义 stress_type 枚举
        ↓
core_pilot cases               正常难度下的「标准卷」
        ↓
stress variants（规划中）       单因素变体，独立文件
        ↓
run_benchmark + 三框架 adapter  同一 case、同一模型配置下跑
        ↓
evaluator + gold/rubric          结构检查 + 任务得分 + 安全 rubric
```

Healthcare 四个任务（H1/H2/H4/H5）压的是**证据、分诊、摘要、拒答**；E-commerce 四个（E1/E2/E3/E5）压的是**趋势合成、约束推荐、政策判断、多步工具**。两类 vertical 故意形成对比，stress 也沿这个分工选_primary scenario_。

## 八个任务各自「主要压什么」

| Task | 核心能力 | 主 stress | 想暴露的问题 |
|---|---|---|---|
| H1 | 证据问答 | `conflicting_evidence` | 遇矛盾文献能否承认不确定，而非硬选一边 |
| H2 | 症状分诊 | `ambiguous_input` | 信息不足时能否保守分诊，而非假精确 |
| H4 | 病历摘要 | `long_context` | 对话很长时是否漏提、 hallucinate |
| H5 | 边界/拒答 | `policy_or_safety_trap` | 对抗性请求下是否仍遵守 boundary |
| E1 | 趋势研究 | `conflicting_evidence` | 多源数据矛盾时能否识别 mixed/insufficient |
| E2 | 商品推荐 | `missing_information` | 缺字段时是否瞎编评分，而非排除或降级 |
| E3 | 退换货政策 | `policy_or_safety_trap` | 客户施压时是否违规放行 refund |
| E5 | 客服工具链 | `tool_failure` | 工具报错后能否恢复，而非整 run 崩溃 |

八种 `stress_type` 在八条主线上各出现一次；`standard` 留给 base case，`repeated_run` 通过同一 case 多次运行测稳定性，不另造输入。

## 当前阶段

现在是**设计冻结、fixture 未写**阶段：思路和三份 rubric 已就绪，等 Chloe 确认 schema 字段后再生成 stress case JSON。此前不跑模型、不改 core task、不改 schema。

更多项目背景见仓库 `README.md` 和 `framework_comparison_rationale.md`。
