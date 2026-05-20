"""构建人工复核问答卡片 — 生成 {run_id}_questions.md"""

import os
from datetime import datetime
from typing import Optional
from error_governance.models.diagnosis_result import DiagnosisResult
from error_governance.models.human_review import (
    HumanReviewCard, HUMAN_REVIEW_RESULTS, EVIDENCE_REVIEW_RESULTS,
)
from error_governance.config import ARTIFACTS_HUMAN_QUESTIONS


def save_question_file(diagnosis: DiagnosisResult, review_card: HumanReviewCard, run_id: str = "") -> str:
    """生成单个治理条目的问答卡片 → human_questions/{run_id}/{gid}_question.md"""
    q_dir = os.path.join(ARTIFACTS_HUMAN_QUESTIONS, run_id) if run_id else ARTIFACTS_HUMAN_QUESTIONS
    os.makedirs(q_dir, exist_ok=True)
    path = os.path.join(q_dir, f"{diagnosis.governance_id}_question.md")

    d = diagnosis
    evi = d.evidence
    suf = "充足" if evi.sufficiency.sufficient_for_diagnosis else "不足"

    md = f"""# 人工复核 — {d.governance_id}

- **error_code**: {d.error_input.error_code or '无'}
- **error_message**: {d.error_input.error_message[:100]}
- **AI 诊断**: {d.features.major_category} / {d.features.minor_category}
- **路径**: {d.recommended_path.value}
- **优先级**: {d.priority.priority.value}（{d.priority.total_score} 分）
- **证据**: {suf}（共 {evi.total_evidence_count} 条）
- **置信度**: {d.confidence_score:.0%}
- **报告**: artifacts/diagnosis_reports/{d.governance_id}_report.md
- **复核卡**: artifacts/review_cards/{d.governance_id}_review_card.md

## 复核结论

human_review_result:
evidence_review_result:
is_reproducible:
is_optimization_needed:
human_review_comment:
path_adjustment:
priority_adjustment:
next_action:
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def build_batch_question_file(
    run_id: str,
    results: list,  # list of PipelineResult
    input_file: str = "",
) -> str:
    """生成批量人工确认问答卡片文件，返回文件路径"""
    os.makedirs(ARTIFACTS_HUMAN_QUESTIONS, exist_ok=True)
    path = os.path.join(ARTIFACTS_HUMAN_QUESTIONS, f"{run_id}_questions.md")

    lines = _build_markdown(run_id, results, input_file)

    with open(path, "w", encoding="utf-8") as f:
        f.write(lines)
    return path


def _build_markdown(run_id: str, results: list, input_file: str) -> str:
    success_results = [r for r in results if r.success]
    failed_results = [r for r in results if not r.success]

    now = datetime.now().isoformat()
    response_path = f"artifacts/human_questions/{run_id}_user_response.md"

    md = f"""# 待人工确认事项

**Run ID**: {run_id}
**生成时间**: {now}
**输入文件**: {input_file}
**诊断条目**: {len(results)} 条（成功 {len(success_results)} / 失败 {len(failed_results)}）
**状态**: ⏸ WAITING_FOR_HUMAN

---

## 使用说明

请逐条确认以下报错诊断结果。复制"反馈模板"部分，为每个 error_id 填写后，保存为：

```
{response_path}
```

完成后执行：

```
python scripts/resume_pipeline.py --run-id {run_id} --review-input {response_path}
```

---

## 可选人工结论

### human_review_result（必填，九选一）
"""
    for i, v in enumerate(HUMAN_REVIEW_RESULTS, 1):
        md += f"- {v}\n"

    md += """
### evidence_review_result（必填，六选一）
"""
    for v in EVIDENCE_REVIEW_RESULTS:
        md += f"- {v}\n"

    md += """
### is_reproducible（必填）
- 是
- 否
- 不确定

### is_optimization_needed（必填）
- 是
- 否
- 待讨论

---

## 诊断结果详情

"""
    # 成功条目
    for r in success_results:
        md += _build_item_section(r)

    # 失败条目
    if failed_results:
        md += "---\n\n## 诊断失败的条目\n\n"
        for r in failed_results:
            md += f"### error_id: {r.governance_id}\n"
            md += f"- **状态**: ❌ 诊断失败 (Step {r.blocked_at})\n"
            md += f"- **原因**: {r.block_reason}\n\n"

    # 反馈模板
    md += """---

## 用户反馈模板

请复制以下模板，为每个 error_id 填写后保存为上述文件路径。
每个字段必须填写，枚举值必须从上述可选结论中选择。

"""
    for r in success_results:
        d = r.diagnosis
        md += f"""### error_id: {r.governance_id}

human_review_result:
evidence_review_result:
is_reproducible:
is_optimization_needed:
human_review_comment:
path_adjustment:
priority_adjustment:
next_action:

"""
    return md


def _build_item_section(result) -> str:
    """构建单条诊断详情"""
    d = result.diagnosis
    gid = result.governance_id
    inp = d.error_input
    evi = d.evidence

    # 需要确认的问题
    questions = []
    if not evi.sufficiency.sufficient_for_diagnosis:
        questions.append("- ⚠️ 证据不足以支撑诊断，是否仍进入治理？")
    if evi.unavailable_sources:
        questions.append(f"- ⚠️ 以下数据源不可用: {', '.join(evi.unavailable_sources)}，是否接受当前证据水平？")
    if d.confidence_score < 0.5:
        questions.append(f"- ⚠️ AI 置信度仅 {d.confidence_score:.0%}，是否信任当前诊断结论？")
    if d.priority.priority.value in ("P0", "P1"):
        questions.append(f"- 📌 优先级为 {d.priority.priority.value}，是否同意立即治理？")
    if not questions:
        questions.append("- 诊断结论是否准确？")

    suf = "充足" if evi.sufficiency.sufficient_for_diagnosis else "不足"
    sources = ', '.join(evi.unavailable_sources) if evi.unavailable_sources else "无"

    exp = d.experience
    exp_issues = []
    for dim, sev_attr in [("时机", "timing_severity"), ("形式", "form_severity"),
                           ("文案", "copy_severity"), ("交互", "interaction_severity")]:
        sev = getattr(exp, sev_attr)
        if sev.value != "轻微":
            issue = getattr(exp, f"{sev_attr.replace('_severity', '')}_issue", "")
            exp_issues.append(f"- {dim}: {sev.value} — {issue}" if issue else f"- {dim}: {sev.value}")

    md = f"""### error_id: {gid}

| 字段 | 值 |
|------|-----|
| error_code | {inp.error_code or '无'} |
| error_message | {inp.error_message[:100]} |
| AI 诊断摘要 | {d.features.major_category} / {d.features.minor_category} |
| 推荐治理路径 | {d.recommended_path.value} |
| 优先级 | {d.priority.priority.value}（{d.priority.total_score} 分）|
| 证据充分性 | {suf}（共 {evi.total_evidence_count} 条，强相关 {evi.strong_relevance_count}，中相关 {evi.medium_relevance_count}）|
| 不可用数据源 | {sources} |
| AI 置信度 | {d.confidence_score:.0%} |
| 诊断报告 | artifacts/diagnosis_reports/{gid}_report.md |
| 复核卡 | artifacts/review_cards/{gid}_review_card.md |

#### 体验评估摘要
{chr(10).join(exp_issues) if exp_issues else '无显著体验问题'}

#### 需要确认的问题
{chr(10).join(questions)}

"""

    # 证据详情
    if evi.items:
        md += "#### 证据清单\n"
        for item in evi.items:
            md += f"- [{item.relevance_level.value}] [{item.source_type.value}] {item.evidence_summary} (可信度: {item.confidence.value})\n"
        md += "\n"

    md += "---\n\n"
    return md
