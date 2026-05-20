"""Pydantic 数据模型 — 对应 output_schema.md + state/ 模板"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


# ── 输入 ──────────────────────────────────────────

class ErrorInput(BaseModel):
    error_code: Optional[str] = Field(default=None, alias="错误码")
    error_message: str = Field(alias="报错提示")
    url: Optional[str] = Field(default=None, alias="URL")
    page_route: Optional[str] = Field(default=None, alias="页面路由")
    trigger_scenario: Optional[str] = Field(default=None, alias="触发场景")
    error_count: int = Field(default=1, alias="页面报错次数")

    class Config:
        populate_by_name = True


# ── 特征提取（Step 02）────────────────────────────

class ErrorFeatures(BaseModel):
    major_category: str = ""          # 大类
    minor_category: str = ""          # 小类
    task_type: str = ""               # 任务类型
    validation_logic: str = ""        # 校验逻辑
    error_reason: str = ""            # 报错原因
    business_module: str = ""         # 涉及业务模块
    search_keywords: list[str] = []   # 检索关键词


# ── 证据（Step 04-05）─────────────────────────────

class RelevanceLevel(str, Enum):
    STRONG = "强相关"
    MEDIUM = "中相关"
    WEAK = "弱相关"
    IRRELEVANT = "不相关"

class ConfidenceLevel(str, Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

class EvidenceSource(str, Enum):
    CUSTOMER_FEEDBACK = "客户反馈"
    TICKET = "工单"
    TRACKING = "埋点"
    BUSINESS_KB = "业务知识库"
    DESIGN_KB = "设计知识库"
    HISTORICAL_CASE = "历史案例"

class EvidenceItem(BaseModel):
    evidence_id: str = ""
    source_type: EvidenceSource
    source_name: str = ""
    matched_fields: list[str] = []
    relevance_level: RelevanceLevel = RelevanceLevel.IRRELEVANT
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    evidence_summary: str = ""
    supports: list[str] = []
    limitations: list[str] = []

class EvidenceConflict(BaseModel):
    has_conflict: bool = False
    conflict_type: str = ""
    handling_result: str = ""

class EvidenceSufficiency(BaseModel):
    sufficient_for_diagnosis: bool = False
    sufficient_for_priority_scoring: bool = False
    sufficient_for_effect_estimation: bool = False

class EvidenceSummary(BaseModel):
    total_evidence_count: int = 0
    strong_relevance_count: int = 0
    medium_relevance_count: int = 0
    weak_relevance_count: int = 0
    unavailable_sources: list[str] = []
    items: list[EvidenceItem] = []
    conflict: EvidenceConflict = EvidenceConflict()
    sufficiency: EvidenceSufficiency = EvidenceSufficiency()


# ── 体验评估（Step 06）────────────────────────────

class ExperienceSeverity(str, Enum):
    CRITICAL = "严重"
    MODERATE = "一般"
    MINOR = "轻微"

class ExperienceAssessment(BaseModel):
    timing_issue: str = ""
    timing_severity: ExperienceSeverity = ExperienceSeverity.MINOR
    form_issue: str = ""
    form_severity: ExperienceSeverity = ExperienceSeverity.MINOR
    copy_issue: str = ""
    copy_severity: ExperienceSeverity = ExperienceSeverity.MINOR
    interaction_issue: str = ""
    interaction_severity: ExperienceSeverity = ExperienceSeverity.MINOR


# ── 优先级评分（Step 07）─────────────────────────

class PriorityLevel(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class PriorityAssessment(BaseModel):
    journey_impact_score: float = 0
    experience_violation_score: float = 0
    customer_impact_score: float = 0
    error_scale_score: float = 0
    fix_feasibility_score: float = 0
    total_score: float = 0
    priority: PriorityLevel = PriorityLevel.P3


# ── 成效预估（Step 08）────────────────────────────

class EffectEstimation(BaseModel):
    primary_metric: str = ""
    estimated_change: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    basis: list[str] = []
    limitations: list[str] = []


# ── 路径判定（Step 09）────────────────────────────

class ImplementationPath(str, Enum):
    A_COPY = "A.纯文案发布"
    B_CONFIG = "B.配置化体验"
    C_FRONTEND = "C.前端交互改造"
    D_BACKEND = "D.后端规则逻辑改造"


# ── 综合诊断报告（Step 10）────────────────────────

class DiagnosisReport(BaseModel):
    governance_id: str = ""
    error_input: ErrorInput
    features: ErrorFeatures = ErrorFeatures()
    evidence: EvidenceSummary = EvidenceSummary()
    experience: ExperienceAssessment = ExperienceAssessment()
    priority: PriorityAssessment = PriorityAssessment()
    effect: EffectEstimation = EffectEstimation()
    recommended_path: ImplementationPath = ImplementationPath.A_COPY
    path_rationale: str = ""
    verification_plan: str = ""
    optimization_direction: str = ""
    confidence_score: float = 0.0  # 0-1


# ── 人工复核卡（Step 11）─────────────────────────

class ReviewCard(BaseModel):
    governance_id: str = ""
    error_message: str = ""
    ai_summary: str = ""
    recommended_path: str = ""
    priority: str = ""
    evidence_summary_text: str = ""
    review_items: list[str] = []
    review_conclusion: str = ""       # 人工填写
    reviewer: str = ""
    review_time: str = ""
    notes: str = ""


# ── 运行日志 ──────────────────────────────────────

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
    current_status: str = "待评估"


# ── 治理台账条目 ──────────────────────────────────

class GovernanceLedgerEntry(BaseModel):
    error_id: str = ""
    error_code: str = ""
    error_message: str = ""
    current_status: str = "待评估"
    diagnosis_report_path: str = ""
    review_card_path: str = ""
    evidence_total_count: int = 0
    evidence_sufficiency_status: str = ""
    evidence_conflict_flag: bool = False
    human_review_result: str = ""
    human_review_comment: str = ""
    reviewer: str = ""
    review_time: str = ""
