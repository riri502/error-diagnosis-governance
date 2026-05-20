"""Step 07-08: 优先级评分 + 成效预估 — DOC-04 + DOC-05"""

from error_governance.models.diagnosis_result import (
    PriorityAssessment, PriorityLevel, EffectEstimate, ExperienceSeverity,
)
from error_governance.models.evidence import ConfidenceLevel, EvidenceSummary
from error_governance.config import PRIORITY_WEIGHTS, PRIORITY_THRESHOLDS


def assess_priority(error_item, features, evidence, experience) -> PriorityAssessment:
    sev_score = {ExperienceSeverity.CRITICAL: 40, ExperienceSeverity.MODERATE: 25, ExperienceSeverity.MINOR: 5}

    journey = _score_journey(features)
    experience_v = sum(sev_score.get(getattr(experience, attr), 0)
                       for attr in ["timing_severity", "form_severity", "copy_severity", "interaction_severity"])
    experience_v = min(experience_v, 100)
    customer = 30 if "客户反馈" in evidence.unavailable_sources else 50
    scale = _score_scale(error_item.error_count)
    fix = _score_fix(features)

    total = (
        journey * PRIORITY_WEIGHTS["journey_impact"]
        + experience_v * PRIORITY_WEIGHTS["experience_violation"]
        + customer * PRIORITY_WEIGHTS["customer_impact"]
        + scale * PRIORITY_WEIGHTS["error_scale"]
        + fix * PRIORITY_WEIGHTS["fix_feasibility"]
    )

    priority = PriorityLevel.P3
    for t, lvl in PRIORITY_THRESHOLDS:
        if total >= t:
            priority = lvl
            break

    return PriorityAssessment(
        journey_impact_score=round(journey, 1),
        experience_violation_score=round(experience_v, 1),
        customer_impact_score=round(customer, 1),
        error_scale_score=round(scale, 1),
        fix_feasibility_score=round(fix, 1),
        total_score=round(total, 1),
        priority=priority,
    )


def _score_journey(features):
    m = features.major_category
    if "权限" in m: return 75
    if "系统异常" in m: return 85
    if "校验" in m: return 60
    if features.minor_category == "状态不允许操作": return 80
    return 50


def _score_scale(count):
    if count >= 5000: return 95
    if count >= 1000: return 80
    if count >= 500: return 65
    if count >= 100: return 50
    return 30


def _score_fix(features):
    m = features.major_category
    if "校验" in m: return 85
    if "权限" in m: return 65
    if "系统异常" in m: return 40
    return 50


def estimate_effect(error_item, features, evidence, priority) -> EffectEstimate:
    count = error_item.error_count
    major = features.major_category

    if "校验" in major:
        metric, change = "任务一次性完成率 / 报错压降率", f"预计报错量下降 60-80%（约 {int(count * 0.7)} 次）"
    elif "权限" in major:
        metric, change = "报错压降率", f"入口屏蔽后弹窗次数降为零，约减少 {count} 次"
    elif "系统异常" in major:
        metric, change = "报错压降率 / 满意度得分", f"弹窗→Toast/占位消除阻断，约减少 {int(count * 0.9)} 次"
    else:
        metric, change = "报错压降率 / 关键步骤成功率", "预计报错量下降 30-50%"

    conf = ConfidenceLevel.LOW
    if evidence.sufficiency.sufficient_for_effect_estimation:
        conf = ConfidenceLevel.HIGH
    elif evidence.sufficiency.sufficient_for_diagnosis:
        conf = ConfidenceLevel.MEDIUM

    return EffectEstimate(
        primary_metric=metric, estimated_change=change, confidence=conf,
        basis=[f"报错频次: {count}次", f"报错类型: {major}"],
        limitations=evidence.unavailable_sources if evidence.unavailable_sources else [],
    )
