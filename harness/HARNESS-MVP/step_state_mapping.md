# HARNESS-MVP 执行步骤与业务状态映射

## 说明

HARNESS-MVP 有两个视角的记录体系：

- **run_log_schema.md**：记录 SKILL-01 内部执行步骤的状态，粒度较细。每个子步骤是否成功、是否异常，用于调试和可追溯性。
- **state_transition.md**：记录报错条目在治理流程中的外部业务状态，粒度较粗。状态变更触发问题池分流和人工复核节点。

关键词生成（step_03）属于 SKILL-01 内部执行步骤，不单独映射为外部业务状态。

## 映射表

| run_log_schema 执行步骤 | state_transition 业务状态 |
|------------------------|------------------------|
| step_01_input_ok | 待评估 → 诊断中 |
| step_02_feature_ok | 诊断中（内部）|
| step_03_keyword_gen_ok | 诊断中（内部，无独立状态）|
| step_04_evidence_search_ok | 证据检索中 |
| step_05_evidence_relevance_ok | 证据相关性判定中 |
| step_06_experience_ok | 诊断中（内部）|
| step_07_priority_ok | 诊断中（内部）|
| step_08_effect_ok | 诊断中（内部）|
| step_09_path_ok | 诊断中（内部）|
| step_10_report_ok | 诊断中 → 待人工复核 |
| step_11_review_card_ok | 待人工复核 |
| —（人工填写结论）| 待人工复核 → 人工复核完成 |
| —（HARNESS 分流）| 人工复核完成 → 治理候选/暂未复现/无需优化/待补充信息/规则修正/埋点缺口/证据不足/证据冲突/低置信诊断 |

## 异常映射

| 异常类型（run_log_schema）| 状态流转 |
|--------------------------|---------|
| 缺字段（step_01 失败）| → 待补充信息池 |
| 低置信（step_05/06 弱相关或无证据）| → 低置信诊断池 |
| 无证据（step_04 所有源不可用）| → 证据不足池 |
| 证据冲突（step_05 多源指向不一致）| → 证据冲突池 |
| 规则冲突（step_06/09 无法判定）| → 规则修正池 |
