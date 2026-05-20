"""工作流状态枚举与流转规则

===== 实现与规则文档冲突报告 =====

1. "已完成" vs "已归档"
   - 本实现: ErrorItemStatus 使用 "已完成" 作为终态
   - 规则文档 (state_transition.md): 状态枚举使用 "已归档"
   - 处理: 保留用户指定的 "已完成"

2. "证据不足"/"证据冲突" 作为 ErrorItemStatus
   - 规则文档 (DOC-06): 证据不足和证据冲突是问题池名称
   - 规则文档 (state_transition.md): 证据不足/冲突是证据相关性判定的内部分支
   - 处理: 保留为用户指定的 ErrorItemStatus，同时映射对应问题池

3. "治理候选" vs "治理候选池"
   - 规则文档: "治理候选池" 是问题池名称
   - 处理: 条目状态用 "治理候选"，问题池名保持 "治理候选池"

===== 参考 =====
- rules/DOC-06_异常分流与问题池规则.md
- rules/DOC-07_人工复核结论与状态流转规则.md
- harness/HARNESS-MVP/state_transition.md
"""

from datetime import datetime
from enum import Enum
from typing import Tuple
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════
# Run 级别状态
# ═══════════════════════════════════════════════════

class RunStatus(str, Enum):
    CREATED = "CREATED"
    INPUT_VALIDATED = "INPUT_VALIDATED"
    DIAGNOSIS_RUNNING = "DIAGNOSIS_RUNNING"
    DIAGNOSIS_COMPLETED = "DIAGNOSIS_COMPLETED"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    HUMAN_REVIEW_RECEIVED = "HUMAN_REVIEW_RECEIVED"
    STATE_UPDATE_RUNNING = "STATE_UPDATE_RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ═══════════════════════════════════════════════════
# ErrorItem 级别状态
# ═══════════════════════════════════════════════════

class ErrorItemStatus(str, Enum):
    PENDING = "待评估"
    DIAGNOSING = "诊断中"
    EVIDENCE_SEARCHING = "证据检索中"
    EVIDENCE_RELEVANCE = "证据相关性判定中"
    WAITING_HUMAN = "待人工复核"
    REVIEWED = "人工复核完成"

    GOVERNANCE_CANDIDATE = "治理候选"
    NOT_REPRODUCED = "暂未复现"
    NO_OPTIMIZATION = "无需优化"
    NEED_INFO = "待补充信息"
    LOW_CONFIDENCE = "低置信诊断"
    RULE_FIX = "规则修正"
    EVIDENCE_INSUFFICIENT = "证据不足"
    EVIDENCE_CONFLICT = "证据冲突"
    TRACKING_GAP = "埋点缺口"
    PRODUCT_CONFIRM = "产品确认"
    DEV_CONFIRM = "研发确认"
    COMPLETED = "已完成"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"


# ═══════════════════════════════════════════════════
# Run 级流转表
# ═══════════════════════════════════════════════════

RUN_TRANSITIONS: dict[RunStatus, list[RunStatus]] = {
    RunStatus.CREATED:               [RunStatus.INPUT_VALIDATED, RunStatus.FAILED],
    RunStatus.INPUT_VALIDATED:       [RunStatus.DIAGNOSIS_RUNNING, RunStatus.FAILED],
    RunStatus.DIAGNOSIS_RUNNING:     [RunStatus.DIAGNOSIS_COMPLETED, RunStatus.FAILED],
    RunStatus.DIAGNOSIS_COMPLETED:   [RunStatus.WAITING_FOR_HUMAN],
    RunStatus.WAITING_FOR_HUMAN:     [RunStatus.HUMAN_REVIEW_RECEIVED],
    RunStatus.HUMAN_REVIEW_RECEIVED: [RunStatus.STATE_UPDATE_RUNNING],
    RunStatus.STATE_UPDATE_RUNNING:  [RunStatus.COMPLETED, RunStatus.WAITING_FOR_HUMAN],
    RunStatus.COMPLETED:             [],
    RunStatus.FAILED:                [RunStatus.CREATED],
}


# ═══════════════════════════════════════════════════
# ErrorItem 级流转表
# ═══════════════════════════════════════════════════

ITEM_TRANSITIONS: dict[ErrorItemStatus, list[ErrorItemStatus]] = {
    # 初始 → 诊断
    ErrorItemStatus.PENDING: [ErrorItemStatus.DIAGNOSING],

    # 诊断中 → 内部步骤 / 分流
    ErrorItemStatus.DIAGNOSING: [
        ErrorItemStatus.EVIDENCE_SEARCHING,
        ErrorItemStatus.EVIDENCE_RELEVANCE,
        ErrorItemStatus.WAITING_HUMAN,
        ErrorItemStatus.LOW_CONFIDENCE,
        ErrorItemStatus.EVIDENCE_INSUFFICIENT,
        ErrorItemStatus.EVIDENCE_CONFLICT,
        ErrorItemStatus.NEED_INFO,
    ],

    ErrorItemStatus.EVIDENCE_SEARCHING: [
        ErrorItemStatus.EVIDENCE_RELEVANCE,
        ErrorItemStatus.EVIDENCE_INSUFFICIENT,
    ],

    ErrorItemStatus.EVIDENCE_RELEVANCE: [
        ErrorItemStatus.DIAGNOSING,
        ErrorItemStatus.EVIDENCE_INSUFFICIENT,
        ErrorItemStatus.EVIDENCE_CONFLICT,
        ErrorItemStatus.LOW_CONFIDENCE,
    ],

    # 待人工复核 → 分流
    ErrorItemStatus.WAITING_HUMAN: [
        ErrorItemStatus.REVIEWED,
        ErrorItemStatus.GOVERNANCE_CANDIDATE,
        ErrorItemStatus.NOT_REPRODUCED,
        ErrorItemStatus.NO_OPTIMIZATION,
        ErrorItemStatus.NEED_INFO,
        ErrorItemStatus.RULE_FIX,
        ErrorItemStatus.TRACKING_GAP,
        ErrorItemStatus.PRODUCT_CONFIRM,
        ErrorItemStatus.DEV_CONFIRM,
        ErrorItemStatus.COMPLETED,
    ],

    ErrorItemStatus.REVIEWED: [
        ErrorItemStatus.GOVERNANCE_CANDIDATE,
        ErrorItemStatus.NOT_REPRODUCED,
        ErrorItemStatus.NO_OPTIMIZATION,
        ErrorItemStatus.NEED_INFO,
        ErrorItemStatus.RULE_FIX,
        ErrorItemStatus.TRACKING_GAP,
        ErrorItemStatus.PRODUCT_CONFIRM,
        ErrorItemStatus.DEV_CONFIRM,
        ErrorItemStatus.COMPLETED,
    ],

    # 终态 / 可重入
    ErrorItemStatus.GOVERNANCE_CANDIDATE:  [ErrorItemStatus.COMPLETED],
    ErrorItemStatus.NOT_REPRODUCED:        [ErrorItemStatus.PENDING, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.NO_OPTIMIZATION:       [ErrorItemStatus.COMPLETED],
    ErrorItemStatus.NEED_INFO:             [ErrorItemStatus.PENDING, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.LOW_CONFIDENCE:        [ErrorItemStatus.WAITING_HUMAN, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.RULE_FIX:              [ErrorItemStatus.PENDING, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.EVIDENCE_INSUFFICIENT: [ErrorItemStatus.PENDING, ErrorItemStatus.WAITING_HUMAN, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.EVIDENCE_CONFLICT:     [ErrorItemStatus.WAITING_HUMAN, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.TRACKING_GAP:          [ErrorItemStatus.PENDING, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.PRODUCT_CONFIRM:       [ErrorItemStatus.WAITING_HUMAN, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.DEV_CONFIRM:           [ErrorItemStatus.WAITING_HUMAN, ErrorItemStatus.COMPLETED],
    ErrorItemStatus.COMPLETED:             [],
}


# ═══════════════════════════════════════════════════
# 流转校验
# ═══════════════════════════════════════════════════

def transition_run(current: RunStatus, target: RunStatus) -> Tuple[bool, str]:
    if current == target:
        return True, ""
    allowed = RUN_TRANSITIONS.get(current, [])
    if target in allowed:
        return True, ""
    names = [s.value for s in allowed]
    return False, (
        f"非法流转 RunStatus: {current.value} → {target.value}。"
        f"允许: {names if names else '(终态)'}"
    )


def transition_item(current: ErrorItemStatus, target: ErrorItemStatus) -> Tuple[bool, str]:
    if current == target:
        return True, ""
    allowed = ITEM_TRANSITIONS.get(current, [])
    if target in allowed:
        return True, ""
    names = [s.value for s in allowed]
    return False, (
        f"非法流转 ErrorItemStatus: {current.value} → {target.value}。"
        f"允许: {names if names else '(终态)'}"
    )


def assert_transition_run(current: RunStatus, target: RunStatus):
    ok, msg = transition_run(current, target)
    if not ok:
        raise ValueError(msg)


def assert_transition_item(current: ErrorItemStatus, target: ErrorItemStatus):
    ok, msg = transition_item(current, target)
    if not ok:
        raise ValueError(msg)


# ═══════════════════════════════════════════════════
# 人工复核结论 → 状态映射 (DOC-07)
# ═══════════════════════════════════════════════════

REVIEW_TO_STATUS: dict[str, ErrorItemStatus] = {
    "评估准确，进入治理":       ErrorItemStatus.GOVERNANCE_CANDIDATE,
    "评估基本准确，需调整建议":  ErrorItemStatus.GOVERNANCE_CANDIDATE,
    "评估不准确":               ErrorItemStatus.RULE_FIX,
    "条目暂未复现":             ErrorItemStatus.NOT_REPRODUCED,
    "条目无需优化":             ErrorItemStatus.NO_OPTIMIZATION,
    "需补充信息":               ErrorItemStatus.NEED_INFO,
    "需产品确认":               ErrorItemStatus.PRODUCT_CONFIRM,
    "需研发确认":               ErrorItemStatus.DEV_CONFIRM,
    "需补充埋点":               ErrorItemStatus.TRACKING_GAP,
}

EVIDENCE_REVIEW_TO_STATUS: dict[str, ErrorItemStatus] = {
    "证据不足，暂不进入治理":       ErrorItemStatus.EVIDENCE_INSUFFICIENT,
    "证据冲突，需产品 / 运营确认":   ErrorItemStatus.EVIDENCE_CONFLICT,
    "埋点证据缺失，需补充埋点":      ErrorItemStatus.TRACKING_GAP,
}

STATUS_TO_POOL: dict[ErrorItemStatus, str] = {
    ErrorItemStatus.GOVERNANCE_CANDIDATE:  "治理候选池",
    ErrorItemStatus.NOT_REPRODUCED:        "暂未复现池",
    ErrorItemStatus.NO_OPTIMIZATION:       "无需优化归档",
    ErrorItemStatus.NEED_INFO:             "待补充信息池",
    ErrorItemStatus.LOW_CONFIDENCE:        "低置信诊断池",
    ErrorItemStatus.RULE_FIX:              "规则修正池",
    ErrorItemStatus.EVIDENCE_INSUFFICIENT: "证据不足池",
    ErrorItemStatus.EVIDENCE_CONFLICT:     "证据冲突池",
    ErrorItemStatus.TRACKING_GAP:          "埋点缺口池",
    ErrorItemStatus.PRODUCT_CONFIRM:       "产品确认池",
    ErrorItemStatus.DEV_CONFIRM:           "研发确认池",
}


# ═══════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════

class RunLog(BaseModel):
    run_id: str = ""
    error_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    step_01_input_ok: bool = False
    step_02_feature_ok: bool = False
    step_03_keyword_gen_ok: bool = False
    step_04_evidence_search_ok: bool = False
    step_05_evidence_relevance_ok: bool = False
    step_06_experience_ok: bool = False
    step_07_priority_ok: bool = False
    step_08_effect_ok: bool = False
    step_09_path_ok: bool = False
    step_10_report_ok: bool = False
    step_11_review_card_ok: bool = False
    evidence_sources_available: list[str] = []
    evidence_sources_unavailable: list[str] = []
    exception_type: str = ""
    current_status: str = ErrorItemStatus.PENDING.value


class WorkflowState(BaseModel):
    governance_id: str
    run_status: RunStatus = RunStatus.CREATED
    item_status: ErrorItemStatus = ErrorItemStatus.PENDING
    run_log: RunLog = RunLog()
    blocked_at: str = ""
    block_reason: str = ""
    human_review_completed: bool = False
    human_review_response: dict = {}

    def transition_item(self, target: ErrorItemStatus):
        """流转到目标状态，校验合法性"""
        assert_transition_item(self.item_status, target)
        self.item_status = target

    def transition_run(self, target: RunStatus):
        """流转 RunStatus"""
        assert_transition_run(self.run_status, target)
        self.run_status = target
