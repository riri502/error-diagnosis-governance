"""DOC-08 多源证据检索 — 本地文件适配器（不编造数据，不可用时标记 unavailable）"""

import os
import json
import csv
from pathlib import Path
from typing import Optional

from error_diagnosis.models import (
    EvidenceItem, EvidenceSource, RelevanceLevel, ConfidenceLevel,
    EvidenceSummary, EvidenceConflict, EvidenceSufficiency,
    ErrorFeatures, ErrorInput,
)
from error_diagnosis.config import (
    KNOWLEDGE_BUSINESS, KNOWLEDGE_DESIGN, KNOWLEDGE_CASES,
)


class BaseRetriever:
    """检索器抽象基类"""
    source_type: EvidenceSource
    source_name: str = ""

    def is_available(self) -> bool:
        """检查数据源是否可用"""
        return False

    def search(self, input: ErrorInput, features: ErrorFeatures) -> list[EvidenceItem]:
        """检索，返回证据列表"""
        return []


class CustomerFeedbackRetriever(BaseRetriever):
    """客户反馈检索器 — 当前不可用（待对接外部系统）"""
    source_type = EvidenceSource.CUSTOMER_FEEDBACK
    source_name = "客户反馈系统"

    def is_available(self) -> bool:
        return False  # Mock: 不可用


class TicketRetriever(BaseRetriever):
    """工单检索器 — 当前不可用（待对接外部系统）"""
    source_type = EvidenceSource.TICKET
    source_name = "工单系统"

    def is_available(self) -> bool:
        return False  # Mock: 不可用


class TrackingRetriever(BaseRetriever):
    """埋点检索器 — 基于本地 Excel/CSV 统计"""
    source_type = EvidenceSource.TRACKING
    source_name = "埋点数据"

    def is_available(self) -> bool:
        # 检查是否有本地埋点统计文件
        return False  # MVP: 暂无专门埋点文件，依赖输入中的 error_count

    def search(self, input: ErrorInput, features: ErrorFeatures) -> list[EvidenceItem]:
        """使用输入报错自身的 error_count 作为基础埋点证据"""
        items = []
        if input.error_count > 0:
            items.append(EvidenceItem(
                evidence_id=f"tracking_{input.error_code or 'no_code'}",
                source_type=EvidenceSource.TRACKING,
                source_name="报错输入统计",
                matched_fields=["error_count"],
                relevance_level=RelevanceLevel.STRONG,
                confidence=ConfidenceLevel.HIGH,
                evidence_summary=f"统计期内报错 {input.error_count} 次",
                supports=["error_scale", "priority_scoring"],
                limitations=["仅含报错次数，缺旅程指标和任务完成数据"],
            ))
        return items


class BusinessKnowledgeRetriever(BaseRetriever):
    """业务知识库检索器 — 基于本地 Markdown 文件"""
    source_type = EvidenceSource.BUSINESS_KB
    source_name = "业务知识库"

    def is_available(self) -> bool:
        return os.path.isdir(KNOWLEDGE_BUSINESS) and bool(
            list(Path(KNOWLEDGE_BUSINESS).glob("*.md"))
        )

    def search(self, input: ErrorInput, features: ErrorFeatures) -> list[EvidenceItem]:
        items = []
        if not self.is_available():
            return items
        for md_file in Path(KNOWLEDGE_BUSINESS).glob("*.md"):
            content = md_file.read_text(encoding="utf-8")[:2000]
            for kw in features.search_keywords:
                if kw and kw in content:
                    items.append(EvidenceItem(
                        evidence_id=f"biz_kb_{md_file.stem}",
                        source_type=EvidenceSource.BUSINESS_KB,
                        source_name=md_file.name,
                        matched_fields=["search_keywords"],
                        relevance_level=RelevanceLevel.MEDIUM,
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_summary=f"业务知识库 [{md_file.stem}] 匹配关键词 [{kw}]",
                        supports=["场景判断", "原因分析"],
                        limitations=["知识库条目可能未覆盖最新业务规则"],
                    ))
                    break
        return items


class DesignKnowledgeRetriever(BaseRetriever):
    """设计知识库检索器 — 基于本地 Markdown 文件"""
    source_type = EvidenceSource.DESIGN_KB
    source_name = "设计知识库"

    def is_available(self) -> bool:
        return os.path.isdir(KNOWLEDGE_DESIGN) and bool(
            list(Path(KNOWLEDGE_DESIGN).glob("*.md"))
        )

    def search(self, input: ErrorInput, features: ErrorFeatures) -> list[EvidenceItem]:
        items = []
        if not self.is_available():
            return items
        for md_file in Path(KNOWLEDGE_DESIGN).glob("*.md"):
            content = md_file.read_text(encoding="utf-8")[:2000]
            for kw in features.search_keywords:
                if kw and kw in content:
                    items.append(EvidenceItem(
                        evidence_id=f"design_kb_{md_file.stem}",
                        source_type=EvidenceSource.DESIGN_KB,
                        source_name=md_file.name,
                        matched_fields=["search_keywords"],
                        relevance_level=RelevanceLevel.MEDIUM,
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_summary=f"设计知识库 [{md_file.stem}] 匹配关键词 [{kw}]",
                        supports=["体验问题判断"],
                        limitations=["知识库条目可能未覆盖最新设计规范"],
                    ))
                    break
        return items


class HistoricalCaseRetriever(BaseRetriever):
    """历史案例检索器 — 基于本地 Markdown 文件"""
    source_type = EvidenceSource.HISTORICAL_CASE
    source_name = "历史案例库"

    def is_available(self) -> bool:
        return os.path.isdir(KNOWLEDGE_CASES) and bool(
            list(Path(KNOWLEDGE_CASES).glob("*.md"))
        )

    def search(self, input: ErrorInput, features: ErrorFeatures) -> list[EvidenceItem]:
        items = []
        if not self.is_available():
            return items
        for md_file in Path(KNOWLEDGE_CASES).glob("*.md"):
            content = md_file.read_text(encoding="utf-8")[:2000]
            for kw in features.search_keywords:
                if kw and kw in content:
                    items.append(EvidenceItem(
                        evidence_id=f"case_{md_file.stem}",
                        source_type=EvidenceSource.HISTORICAL_CASE,
                        source_name=md_file.name,
                        matched_fields=["search_keywords"],
                        relevance_level=RelevanceLevel.MEDIUM,
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_summary=f"历史案例 [{md_file.stem}] 匹配关键词 [{kw}]",
                        supports=["成效预估"],
                        limitations=["案例条件可能与当前场景不完全一致"],
                    ))
                    break
        return items


# ── 检索编排 ─────────────────────────────────────

ALL_RETRIEVERS: list[BaseRetriever] = [
    CustomerFeedbackRetriever(),
    TicketRetriever(),
    TrackingRetriever(),
    BusinessKnowledgeRetriever(),
    DesignKnowledgeRetriever(),
    HistoricalCaseRetriever(),
]


def retrieve_all_evidence(
    input: ErrorInput, features: ErrorFeatures
) -> EvidenceSummary:
    """执行多源证据检索（Step 04），返回 EvidenceSummary"""
    all_items: list[EvidenceItem] = []
    unavailable: list[str] = []

    for retriever in ALL_RETRIEVERS:
        if retriever.is_available():
            items = retriever.search(input, features)
            all_items.extend(items)
        else:
            unavailable.append(retriever.source_type.value)

    # 相关性分级统计
    strong = [i for i in all_items if i.relevance_level == RelevanceLevel.STRONG]
    medium = [i for i in all_items if i.relevance_level == RelevanceLevel.MEDIUM]
    weak = [i for i in all_items if i.relevance_level == RelevanceLevel.WEAK]

    # 冲突检测
    has_conflict = False
    conflict_type = ""
    # 简单冲突检测：工单+埋点数据矛盾
    ticket_items = [i for i in all_items if i.source_type == EvidenceSource.TICKET]
    tracking_items = [i for i in all_items if i.source_type == EvidenceSource.TRACKING]
    if ticket_items and tracking_items:
        # 工单显示已处理但埋点仍高（模拟逻辑）
        has_conflict = False  # MVP: 不做深度冲突检测

    # 充分性判断
    suf = EvidenceSufficiency(
        sufficient_for_diagnosis=len(strong) + len(medium) >= 1,
        sufficient_for_priority_scoring=len(strong) >= 1,
        sufficient_for_effect_estimation=len(strong) >= 2,
    )

    return EvidenceSummary(
        total_evidence_count=len(all_items),
        strong_relevance_count=len(strong),
        medium_relevance_count=len(medium),
        weak_relevance_count=len(weak),
        unavailable_sources=unavailable,
        items=all_items,
        conflict=EvidenceConflict(has_conflict=has_conflict, conflict_type=conflict_type),
        sufficiency=suf,
    )


def get_available_sources() -> list[str]:
    return [r.source_type.value for r in ALL_RETRIEVERS if r.is_available()]


def get_unavailable_sources() -> list[str]:
    return [r.source_type.value for r in ALL_RETRIEVERS if not r.is_available()]
