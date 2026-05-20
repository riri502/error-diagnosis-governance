---
name: error-diagnosis
description: >
  对报错数据进行自动诊断治理。输入报错 CSV 或报错文案+触发场景，
  自动执行特征提取、多源证据检索、体验评估、优先级评分、路径判定，
  输出诊断报告和人工复核卡。需要人工确认时生成问题卡并暂停，
  收到用户反馈后继续执行并分流到问题池。
  触发词：报错诊断, 诊断报错, 报错分析, 报错治理, error diagnosis, 分析报错,
  治理报错, 评估报错, 报错评估, error governance, 运行报错诊断, 执行报错诊断。
---

# error-diagnosis — 报错诊断治理

对报错数据执行自动诊断，评估体验问题（时机/形式/文案/交互），
输出治理优先级（P0-P3）和实施路径（A/B/C/D），
需要人工确认时生成问题卡并暂停，收到反馈后继续执行。

## 触发条件

- 用户上传报错 CSV 文件到 `data/inbox/`
- 用户提供报错文案和触发场景，需要诊断
- 用户说"诊断报错""分析报错""运行报错诊断流程"

## 启动诊断

```bash
python scripts/run_pipeline.py --input data/inbox/errors.csv --run-id RUN_001
```

参数：
- `--input`: 报错 CSV 文件路径（必填）
- `--run-id`: 运行批次 ID，如 `RUN_001`（必填）
- `--no-interact`: 跳过交互式人工确认（可选）

执行内容：
- 读取 CSV → 字段校验 → 11 步 SKILL-01 诊断
- 生成诊断报告 → `artifacts/diagnosis_reports/{run_id}/`
- 生成复核卡 → `artifacts/review_cards/{run_id}/`
- 生成问题卡 → `artifacts/human_questions/{run_id}_questions.md`
- 写入治理台账 → `state/governance_ledger.csv`
- 写入证据登记 → `state/evidence_registry.csv`
- 输出标准化 CSV → `data/processed/{run_id}_standardized_errors.csv`
- 状态置为 `WAITING_FOR_HUMAN`

## 查看状态

```bash
python scripts/check_run_status.py --run-id RUN_001   # 某次运行的详情
python scripts/check_run_status.py                     # 列出所有运行
```

## 当流程暂停等待人工确认时

1. 读取 `artifacts/human_questions/{run_id}_questions.md`
2. 将每个 `error_id` 的诊断摘要、推荐路径、证据充分性、需要确认的问题展示给用户
3. 用户逐条确认，填写反馈模板
4. 保存为 `artifacts/human_questions/{run_id}_user_response.md`

## 恢复执行

```bash
python scripts/resume_pipeline.py --run-id RUN_001 \
  --review-input artifacts/human_questions/RUN_001_user_response.md
```

执行内容：
- 解析用户反馈 → 校验枚举值 → 更新台账和登记表
- 写入问题池 → `state/issue_pools/{对应池}.md`
- 生成 `artifacts/run_logs/{run_id}/state_update_result.md`
- 全量完成则将 run 状态置为 `COMPLETED`

## 反馈模板格式

```markdown
### error_id: GOV_xxx

human_review_result: <九选一>
evidence_review_result: <六选一>
is_reproducible: <是/否/不确定>
is_optimization_needed: <是/否/待讨论>
human_review_comment: <备注>
path_adjustment:
priority_adjustment:
next_action:
```

## 项目内引用文件

### 规则文档
- `rules/DOC-00_数据源盘点与输入输出契约.md` — 字段定义
- `rules/DOC-01_报错特征分类体系.md` — 分类决策树
- `rules/DOC-02_体验问题评估标准.md` — 四维度评估
- `rules/DOC-03_实施路径判定规则.md` — A/B/C/D 路径
- `rules/DOC-04_优先级评分规则.md` — 五维加权
- `rules/DOC-05_成效预估与可信度规则.md`
- `rules/DOC-06_异常分流与问题池规则.md`
- `rules/DOC-07_人工复核结论与状态流转规则.md`
- `rules/DOC-08_多源证据检索与相关性判定规则.md`

### Skill 说明
- `skills/SKILL-01_error_diagnosis/SKILL.md` — 11 步子步骤定义
- `skills/SKILL-01_error_diagnosis/report_template.md`
- `skills/SKILL-01_error_diagnosis/review_card_template.md`

### 运行控制
- `harness/HARNESS-MVP/state_transition.md` — 状态流转图
- `harness/HARNESS-MVP/issue_pool_rules.md` — 分流规则
