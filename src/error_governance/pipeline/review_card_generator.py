"""Step 11: 人工复核卡 → artifacts/review_cards/{run_id}/{error_id}_review_card.md"""

import os
from error_governance.models.diagnosis_result import DiagnosisResult
from error_governance.config import ARTIFACTS_REVIEW_CARDS


def generate(diagnosis: DiagnosisResult, run_id: str) -> str:
    run_dir = os.path.join(ARTIFACTS_REVIEW_CARDS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    gid = diagnosis.governance_id
    path = os.path.join(run_dir, f"{gid}_review_card.md")

    d = diagnosis
    pri = d.priority
    evidence_items = [
        "- [ ] 证据是否与报错场景相关？",
        "- [ ] 是否遗漏重要客户反馈/工单/埋点？",
        "- [ ] 是否有证据冲突？",
        "- [ ] 是否需要补充证据或埋点？",
        "- [ ] 是否同意 AI 对证据相关性的判断？",
    ]

    md = f"""# 人工复核卡

| 字段 | 值 |
|------|-----|
| Run | {run_id} |
| 治理条目 ID | {gid} |
| 报错文案 | {d.error_input.error_message} |
| AI 诊断摘要 | {d.features.major_category}/{d.features.minor_category} — {pri.priority.value}({pri.total_score}分) |
| 推荐路径 | {d.recommended_path.value} |
| 优先级 | {pri.priority.value} |

## 证据复核
{chr(10).join(evidence_items)}

**人工证据复核结论**：
- [ ] 证据充分，诊断可信
- [ ] 证据基本充分，需补充说明
- [ ] 证据不足，暂不进入治理
- [ ] 证据引用不准确，需重新检索
- [ ] 证据冲突，需产品/运营确认
- [ ] 埋点证据缺失，需补充埋点

## 诊断复核
**人工复核结论**（选择一项）：
- [ ] 评估准确，进入治理
- [ ] 评估基本准确，需调整建议
- [ ] 评估不准确
- [ ] 条目暂未复现
- [ ] 条目无需优化
- [ ] 需补充信息
- [ ] 需产品确认
- [ ] 需研发确认
- [ ] 需补充埋点

**复核人**: ________ | **备注**: ________
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path
