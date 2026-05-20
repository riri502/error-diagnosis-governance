"""证据模型"""

from enum import Enum
from pydantic import BaseModel


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
