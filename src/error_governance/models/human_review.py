"""人工复核模型"""

from typing import Optional
from pydantic import BaseModel

# ── 枚举 ──

HUMAN_REVIEW_RESULTS = [
    "评估准确，进入治理",
    "评估基本准确，需调整建议",
    "评估不准确",
    "条目暂未复现",
    "条目无需优化",
    "需补充信息",
    "需产品确认",
    "需研发确认",
    "需补充埋点",
]

EVIDENCE_REVIEW_RESULTS = [
    "证据充分，诊断可信",
    "证据基本充分，但需补充说明",
    "证据不足，暂不进入治理",
    "证据引用不准确，需重新检索",
    "证据冲突，需产品 / 运营确认",
    "埋点证据缺失，需补充埋点",
]


class HumanReviewCard(BaseModel):
    governance_id: str = ""
    error_code: str = ""
    error_message: str = ""
    ai_summary: str = ""
    recommended_path: str = ""
    priority: str = ""
    evidence_summary_text: str = ""
    evidence_sufficiency: str = ""
    report_path: str = ""
    review_card_path: str = ""
    questions: list[str] = []
    review_items: list[str] = []
    review_conclusion: str = ""
    reviewer: str = ""
    review_time: str = ""
    notes: str = ""


class HumanReviewResponse(BaseModel):
    error_id: str  # governance_id
    error_code: str = ""
    human_review_result: str = ""
    evidence_review_result: str = ""
    is_reproducible: str = ""
    is_optimization_needed: str = ""
    human_review_comment: str = ""
    path_adjustment: str = ""
    priority_adjustment: str = ""
    next_action: str = ""
    reviewer: str = ""


class ParseError(BaseModel):
    error_id: str = ""
    field: str = ""
    message: str = ""
    line_content: str = ""


class ParseResult(BaseModel):
    success: bool = True
    responses: list[HumanReviewResponse] = []
    errors: list[ParseError] = []
    total_items: int = 0
    parsed_items: int = 0
