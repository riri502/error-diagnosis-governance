"""诊断结果模型"""

from enum import Enum
from pydantic import BaseModel
from error_governance.models.error_item import ErrorItem, ErrorFeatures
from error_governance.models.evidence import EvidenceSummary, ConfidenceLevel


class ExperienceSeverity(str, Enum):
    CRITICAL = "严重"
    MODERATE = "一般"
    MINOR = "轻微"


class PriorityLevel(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ImplementationPath(str, Enum):
    A_COPY = "A.纯文案发布"
    B_CONFIG = "B.配置化体验"
    C_FRONTEND = "C.前端交互改造"
    D_BACKEND = "D.后端规则逻辑改造"


class ExperienceAssessment(BaseModel):
    timing_issue: str = ""
    timing_severity: ExperienceSeverity = ExperienceSeverity.MINOR
    form_issue: str = ""
    form_severity: ExperienceSeverity = ExperienceSeverity.MINOR
    copy_issue: str = ""
    copy_severity: ExperienceSeverity = ExperienceSeverity.MINOR
    interaction_issue: str = ""
    interaction_severity: ExperienceSeverity = ExperienceSeverity.MINOR


class PriorityAssessment(BaseModel):
    journey_impact_score: float = 0
    experience_violation_score: float = 0
    customer_impact_score: float = 0
    error_scale_score: float = 0
    fix_feasibility_score: float = 0
    total_score: float = 0
    priority: PriorityLevel = PriorityLevel.P3


class EffectEstimate(BaseModel):
    primary_metric: str = ""
    estimated_change: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    basis: list[str] = []
    limitations: list[str] = []


class DiagnosisResult(BaseModel):
    """综合诊断结果"""
    governance_id: str = ""
    error_input: ErrorItem
    features: ErrorFeatures = ErrorFeatures()
    evidence: EvidenceSummary = EvidenceSummary()
    experience: ExperienceAssessment = ExperienceAssessment()
    priority: PriorityAssessment = PriorityAssessment()
    effect: EffectEstimate = EffectEstimate()
    recommended_path: ImplementationPath = ImplementationPath.A_COPY
    path_rationale: str = ""
    verification_plan: str = ""
    optimization_direction: str = ""
    confidence_score: float = 0.0
