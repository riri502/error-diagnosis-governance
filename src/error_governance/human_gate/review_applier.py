"""应用人工复核结论 — 回写台账、登记表、问题池"""

from datetime import datetime
from error_governance.models.human_review import HumanReviewResponse
from error_governance.models.workflow_state import (
    ErrorItemStatus, REVIEW_TO_STATUS, STATUS_TO_POOL,
    assert_transition_item,
)
from error_governance.state.ledger_writer import update_review


def apply_review(resp: HumanReviewResponse):
    """将人工复核结论写入治理台账"""
    comment = (
        f"证据: {resp.evidence_review_result} | "
        f"可复现: {resp.is_reproducible} | "
        f"需优化: {resp.is_optimization_needed}"
    )
    if resp.human_review_comment:
        comment += f" | 备注: {resp.human_review_comment}"
    if resp.path_adjustment:
        comment += f" | 路径调整: {resp.path_adjustment}"
    if resp.priority_adjustment:
        comment += f" | 优先级调整: {resp.priority_adjustment}"
    if resp.next_action:
        comment += f" | 下一步: {resp.next_action}"

    update_review(
        gov_id=resp.error_id,
        conclusion=resp.human_review_result,
        reviewer=resp.reviewer,
        notes=comment,
    )


def get_pool_for_result(human_review_result: str) -> str:
    """根据 human_review_result 返回对应问题池"""
    status = REVIEW_TO_STATUS.get(human_review_result)
    if status and status in STATUS_TO_POOL:
        return STATUS_TO_POOL[status]
    return "待评估池"


def get_status_for_review(human_review_result: str) -> ErrorItemStatus:
    """根据复核结论返回对应的 ErrorItemStatus"""
    return REVIEW_TO_STATUS.get(human_review_result, ErrorItemStatus.NEED_INFO)
