# 报错诊断治理工具 (Error Diagnosis & Governance Tool)

基于多源数据关联分析的报错智能诊断治理系统。

## 目录结构

- `docs/` — 目标定义、执行清单、架构说明
- `rules/` — 规则文档（DOC-00 到 DOC-11）
- `skills/` — 5 个 Skill 的定义和模板
- `harness/` — 运行控制层（MVP + PROD）
- `scripts/` — 自动化脚本
- `state/` — 台账模板、登记表、问题池
- `data/` — 输入数据（原始/样本/处理结果）
- `knowledge/` — 知识库（业务/设计/案例）
- `artifacts/` — 产出物（诊断报告/复核卡/方案包/回检报告）
- `tests/` — 测试用例

## 当前状态

Phase 0-3：最小诊断主链 + 轻量运行控制 + 人工复核闭环
