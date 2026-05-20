"""DOC-04 优先级评分 + DOC-05 成效预估"""

from error_diagnosis.models import (
    ErrorInput, ErrorFeatures, EvidenceSummary, ExperienceAssessment,
    PriorityAssessment, PriorityLevel, EffectEstimation, ConfidenceLevel,
    EvidenceSufficiency, ExperienceSeverity,
    ImplementationPath,
)
from error_diagnosis.config import PRIORITY_WEIGHTS, PRIORITY_THRESHOLDS


def assess_priority(
    input: ErrorInput,
    features: ErrorFeatures,
    evidence: EvidenceSummary,
    experience: ExperienceAssessment,
) -> PriorityAssessment:
    """按 DOC-04 五维加权评分"""

    # 1. 旅程体验影响 (0-100)
    journey_score = _score_journey_impact(features)
    # 2. 体验标准违规 (0-100)
    experience_score = _score_experience_violation(experience)
    # 3. 客户影响 (0-100)
    customer_score = _score_customer_impact(evidence)
    # 4. 报错规模 (0-100)
    scale_score = _score_error_scale(input, features)
    # 5. 修复可行性 (0-100)
    fix_score = _score_fix_feasibility(features, evidence)

    total = (
        journey_score * PRIORITY_WEIGHTS["journey_impact"]
        + experience_score * PRIORITY_WEIGHTS["experience_violation"]
        + customer_score * PRIORITY_WEIGHTS["customer_impact"]
        + scale_score * PRIORITY_WEIGHTS["error_scale"]
        + fix_score * PRIORITY_WEIGHTS["fix_feasibility"]
    )

    priority = PriorityLevel.P3
    for threshold, level in PRIORITY_THRESHOLDS:
        if total >= threshold:
            priority = level
            break

    return PriorityAssessment(
        journey_impact_score=round(journey_score, 1),
        experience_violation_score=round(experience_score, 1),
        customer_impact_score=round(customer_score, 1),
        error_scale_score=round(scale_score, 1),
        fix_feasibility_score=round(fix_score, 1),
        total_score=round(total, 1),
        priority=priority,
    )


def _score_journey_impact(features: ErrorFeatures) -> float:
    """旅程体验影响评分"""
    major = features.major_category
    minor = features.minor_category
    if "权限" in major:
        return 75  # 阻断核心旅程
    if major == "系统异常类" and "网络" in minor:
        return 85  # 高频阻断
    if major == "数据校验类":
        return 60  # 影响效率但不阻断
    if minor == "状态不允许操作":
        return 80  # 阻断状态变更
    return 50


def _score_experience_violation(experience: ExperienceAssessment) -> float:
    """体验标准违规评分"""
    sev_scores = {ExperienceSeverity.CRITICAL: 40, ExperienceSeverity.MODERATE: 25, ExperienceSeverity.MINOR: 5}
    total = 0
    for sev in [experience.timing_severity, experience.form_severity,
                experience.copy_severity, experience.interaction_severity]:
        total += sev_scores.get(sev, 0)
    return min(total, 100)


def _score_customer_impact(evidence: EvidenceSummary) -> float:
    """客户影响评分（基于证据推断——数据源可用时应有实际数据）"""
    # MVP: 证据中无可用的客户反馈数据
    if "客户反馈" in evidence.unavailable_sources:
        return 30  # 无客户反馈数据，默认低影响
    return 50  # 中性


def _score_error_scale(input: ErrorInput, features: ErrorFeatures) -> float:
    """报错规模评分"""
    count = input.error_count
    if count >= 5000:
        return 95
    elif count >= 1000:
        return 80
    elif count >= 500:
        return 65
    elif count >= 100:
        return 50
    return 30


def _score_fix_feasibility(features: ErrorFeatures, evidence: EvidenceSummary) -> float:
    """修复可行性评分（基于报错类型推断）"""
    major = features.major_category
    if major == "数据校验类":
        return 85  # 通常只需前端调整校验时机/文案
    if major == "权限类":
        return 65  # 需要后端权限接口配合
    if major == "系统异常类":
        return 40  # 需要后端/基础设施改动
    return 50


# ── 成效预估（Step 08）────────────────────────────

def estimate_effect(
    input: ErrorInput,
    features: ErrorFeatures,
    evidence: EvidenceSummary,
    priority: PriorityAssessment,
) -> EffectEstimation:
    """按 DOC-05 预估优化成效，标注可信度"""

    count = input.error_count
    major = features.major_category

    # 基于报错特征预估
    if major == "数据校验类":
        metric = "任务一次性完成率 / 报错压降率"
        change = f"预计报错量下降 60-80%（约 {int(count * 0.7)} 次）"
    elif major == "权限类":
        metric = "报错压降率"
        change = f"入口屏蔽后弹窗次数直接降为零，约减少 {count} 次"
    elif major == "系统异常类":
        metric = "报错压降率 / 满意度得分"
        change = f"弹窗→Toast/占位消除阻断，约减少 {int(count * 0.9)} 次"
    else:
        metric = "报错压降率 / 关键步骤成功率"
        change = f"预计报错量下降 30-50%"

    # 可信度
    if evidence.sufficiency.sufficient_for_effect_estimation:
        conf = ConfidenceLevel.HIGH
    elif evidence.sufficiency.sufficient_for_diagnosis:
        conf = ConfidenceLevel.MEDIUM
    else:
        conf = ConfidenceLevel.LOW

    return EffectEstimation(
        primary_metric=metric,
        estimated_change=change,
        confidence=conf,
        basis=[f"报错频次: {count}次", f"报错类型: {major}", "DOC-05 成效预估规则"],
        limitations=evidence.unavailable_sources if evidence.unavailable_sources else [],
    )


# ── 路径判定（Step 09）────────────────────────────

def determine_path(features: ErrorFeatures, experience: ExperienceAssessment) -> tuple[ImplementationPath, str]:
    """按 DOC-03 判定实施路径"""
    major = features.major_category

    if major == "系统异常类":
        return ImplementationPath.D_BACKEND, "涉及后端服务/基础设施，需要后端改造"
    if major in ["数据校验类", "权限类"]:
        # 优先看是否仅需前端改动
        if experience.form_severity != ExperienceSeverity.CRITICAL:
            return ImplementationPath.C_FRONTEND, "需要调整前端校验时机和提示形式"
        return ImplementationPath.D_BACKEND, "校验逻辑涉及后端接口返回，需前后端协同"

    return ImplementationPath.A_COPY, "问题以文案和引导为主，可走文案发布路径"
