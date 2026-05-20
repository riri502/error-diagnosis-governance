"""报告生成 — 诊断报告 (Markdown) + 人工复核卡 (Markdown)"""

import os
from datetime import datetime
from error_diagnosis.models import (
    DiagnosisReport, ReviewCard, ErrorInput, ErrorFeatures,
    EvidenceSummary, ExperienceAssessment, PriorityAssessment,
    EffectEstimation, ImplementationPath,
)
from error_diagnosis.config import ARTIFACTS_DIAGNOSIS, ARTIFACTS_REVIEW_CARDS


def generate_report(report: DiagnosisReport, run_id: str) -> str:
    """生成 Markdown 诊断报告（Step 10），返回报告文件路径"""
    os.makedirs(ARTIFACTS_DIAGNOSIS, exist_ok=True)
    path = os.path.join(ARTIFACTS_DIAGNOSIS, f"{run_id}_report.md")

    inp = report.error_input
    fea = report.features
    evi = report.evidence
    exp = report.experience
    pri = report.priority
    eff = report.effect

    md = f"""# 报错诊断报告

**治理条目 ID**: {report.governance_id}
**生成时间**: {datetime.now().isoformat()}

---

## 体验问题描述

- **报错文案**: {inp.error_message}
- **错误码**: {inp.error_code or '无'}
- **URL**: {inp.url or '无'}
- **页面路由**: {inp.page_route or '无'}
- **触发场景**: {inp.trigger_scenario or '无'}
- **报错次数**: {inp.error_count}

### 特征分类
- 大类: {fea.major_category}
- 小类: {fea.minor_category}
- 任务类型: {fea.task_type}
- 校验逻辑: {fea.validation_logic}
- 报错原因: {fea.error_reason}
- 涉及模块: {fea.business_module}

---

## 多源证据摘要

### 证据概览
- 已检索数据源: {_fmt_sources(evi)}
- 不可用数据源: {', '.join(evi.unavailable_sources) if evi.unavailable_sources else '无'}
- 强相关证据: {evi.strong_relevance_count} 条
- 中相关证据: {evi.medium_relevance_count} 条
- 弱相关证据: {evi.weak_relevance_count} 条
- 证据冲突: {'是' if evi.conflict.has_conflict else '否'}
- 证据充分性: 诊断{'充足' if evi.sufficiency.sufficient_for_diagnosis else '不足'} / 评分{'充足' if evi.sufficiency.sufficient_for_priority_scoring else '不足'} / 预估{'充足' if evi.sufficiency.sufficient_for_effect_estimation else '不足'}

### 关键证据清单
"""
    for item in evi.items:
        md += f"- [{item.relevance_level.value}] [{item.source_type.value}] {item.evidence_summary} (可信度: {item.confidence.value})\n"

    md += f"""
---

## 体验标准评估
- **时机**: {exp.timing_issue or '无显著问题'} ({exp.timing_severity.value})
- **形式**: {exp.form_issue or '无显著问题'} ({exp.form_severity.value})
- **文案**: {exp.copy_issue or '无显著问题'} ({exp.copy_severity.value})
- **交互**: {exp.interaction_issue or '无显著问题'} ({exp.interaction_severity.value})

---

## 优先级评估
- **综合评分**: {pri.priority.value}（{pri.total_score} 分）
- 旅程体验: {pri.journey_impact_score} | 体验违规: {pri.experience_violation_score} | 客户影响: {pri.customer_impact_score} | 报错规模: {pri.error_scale_score} | 修复可行性: {pri.fix_feasibility_score}

---

## 预计成效
- **主指标**: {eff.primary_metric}
- **预估变化**: {eff.estimated_change}
- **可信度**: {eff.confidence.value}
- **依据**: {'; '.join(eff.basis)}
- **限制**: {'; '.join(eff.limitations) if eff.limitations else '无'}

---

## 实施路径
- **建议路径**: {report.recommended_path.value}
- **判定理由**: {report.path_rationale}

## 优化方向
{report.optimization_direction or '待细化'}

## 回检方案
{report.verification_plan or '待细化（缺少埋点条件则给出埋点方案）'}

## 置信度
{report.confidence_score:.1%}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def _fmt_sources(evi: EvidenceSummary) -> str:
    """格式化已检索数据源列表"""
    sources = set(i.source_type.value for i in evi.items)
    if sources:
        return ', '.join(sources)
    return '无可用数据源'


def generate_review_card(report: DiagnosisReport, run_id: str) -> str:
    """生成 Markdown 人工复核卡（Step 11），返回卡片文件路径"""
    os.makedirs(ARTIFACTS_REVIEW_CARDS, exist_ok=True)
    path = os.path.join(ARTIFACTS_REVIEW_CARDS, f"{run_id}_review_card.md")

    inp = report.error_input
    pri = report.priority

    # 证据复核项
    evidence_review_items = [
        "- [ ] 证据是否与报错场景相关？",
        "- [ ] 是否遗漏重要客户反馈/工单/埋点？",
        "- [ ] 是否有证据冲突？",
        "- [ ] 是否需要补充证据？",
        "- [ ] 是否需要补充埋点？",
        "- [ ] 是否同意 AI 对证据相关性的判断？",
    ]

    md = f"""# 人工复核卡

## 基本信息
| 字段 | 值 |
|------|-----|
| 治理条目 ID | {report.governance_id} |
| 报错文案 | {inp.error_message} |
| AI 诊断摘要 | {report.features.major_category} / {report.features.minor_category} — {pri.priority.value}({pri.total_score}分) |
| 推荐路径 | {report.recommended_path.value} |
| 优先级 | {pri.priority.value} |

## 证据复核
{chr(10).join(evidence_review_items)}

**人工证据复核结论**：
- [ ] 证据充分，诊断可信
- [ ] 证据基本充分，但需补充说明
- [ ] 证据不足，暂不进入治理
- [ ] 证据引用不准确，需重新检索
- [ ] 证据冲突，需产品/运营确认
- [ ] 埋点证据缺失，需补充埋点

## 诊断复核
**人工复核结论**（请选择一项）：
- [ ] 评估准确，进入治理
- [ ] 评估基本准确，需调整建议
- [ ] 评估不准确
- [ ] 条目暂未复现
- [ ] 条目无需优化
- [ ] 需补充信息
- [ ] 需产品确认
- [ ] 需研发确认
- [ ] 需补充埋点

**复核人**: ________
**备注**: ________
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path
