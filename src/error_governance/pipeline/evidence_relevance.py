"""Step 05: 证据相关性判定 — DOC-08 规则"""

from error_governance.models.evidence import EvidenceSummary


def assess(evidence: EvidenceSummary) -> tuple[str, bool]:
    """判定证据充分性，返回 (问题描述, 是否需要人工确认)"""
    if evidence.total_evidence_count == 0:
        return "所有数据源均不可用，无可用证据", True
    if evidence.strong_relevance_count + evidence.medium_relevance_count == 0:
        return f"仅 {evidence.weak_relevance_count} 条弱相关证据，不足以支撑诊断", True
    if evidence.conflict.has_conflict:
        return f"证据冲突: {evidence.conflict.conflict_type}，需人工确认", True
    return "证据充分", False
