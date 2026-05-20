# Agent Instructions

本项目是报错诊断治理工具，遵循 `docs/goal-definition/` 中的目标定义和 `docs/execution-plan/` 中的执行清单。

当前阶段：Phase 0-3（最小诊断主链 + 轻量运行控制 + 人工复核闭环）。

工作约束：
- 规则以 `rules/` 目录为准
- Skill 定义见 `skills/` 目录
- 运行控制见 `harness/HARNESS-MVP/`
- 状态管理见 `state/`
- 当前优先保证诊断准确性、证据可追溯、人工结论可回写
