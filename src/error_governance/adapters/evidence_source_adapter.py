"""多源证据检索适配器 — 本地文件 + Mock 数据源"""

import os
from pathlib import Path
from error_governance.adapters.base_adapter import BaseEvidenceSource
from error_governance.models.evidence import (
    EvidenceItem, EvidenceSource, RelevanceLevel, ConfidenceLevel,
    EvidenceSummary, EvidenceConflict, EvidenceSufficiency,
)
from error_governance.config import KNOWLEDGE_BUSINESS, KNOWLEDGE_DESIGN, KNOWLEDGE_CASES


class CustomerFeedbackRetriever(BaseEvidenceSource):
    """客户反馈 — 当前不可用"""
    source_type = EvidenceSource.CUSTOMER_FEEDBACK

    def is_available(self):
        return False

    def search(self, error_item, features) -> list:
        return []


class TicketRetriever(BaseEvidenceSource):
    """工单 — 当前不可用"""
    source_type = EvidenceSource.TICKET

    def is_available(self):
        return False

    def search(self, error_item, features) -> list:
        return []


class TrackingRetriever(BaseEvidenceSource):
    """埋点 — 基于输入的 error_count"""
    source_type = EvidenceSource.TRACKING

    def is_available(self):
        return True  # 始终可用（使用输入自带统计）

    def search(self, error_item, features) -> list[EvidenceItem]:
        if error_item.error_count > 0:
            return [EvidenceItem(
                evidence_id=f"tracking_{error_item.error_code or 'no_code'}",
                source_type=EvidenceSource.TRACKING,
                source_name="报错输入统计",
                matched_fields=["error_count"],
                relevance_level=RelevanceLevel.STRONG,
                confidence=ConfidenceLevel.HIGH,
                evidence_summary=f"统计期内报错 {error_item.error_count} 次",
                supports=["error_scale", "priority_scoring"],
                limitations=["仅含报错次数，缺旅程指标和任务完成数据"],
            )]
        return []


class BusinessKnowledgeRetriever(BaseEvidenceSource):
    """业务知识库"""
    source_type = EvidenceSource.BUSINESS_KB

    def is_available(self):
        return os.path.isdir(KNOWLEDGE_BUSINESS) and bool(list(Path(KNOWLEDGE_BUSINESS).glob("*.md")))

    def search(self, error_item, features) -> list[EvidenceItem]:
        items = []
        if not self.is_available():
            return items
        for md_file in Path(KNOWLEDGE_BUSINESS).glob("*.md"):
            content = md_file.read_text(encoding="utf-8")[:2000]
            for kw in features.search_keywords:
                if kw and kw in content:
                    items.append(EvidenceItem(
                        evidence_id=f"biz_kb_{md_file.stem}",
                        source_type=EvidenceSource.BUSINESS_KB, source_name=md_file.name,
                        matched_fields=["search_keywords"], relevance_level=RelevanceLevel.MEDIUM,
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_summary=f"业务知识库 [{md_file.stem}] 匹配 [{kw}]",
                        supports=["场景判断", "原因分析"],
                        limitations=["知识库条目可能未覆盖最新业务规则"],
                    ))
                    break
        return items


class DesignKnowledgeRetriever(BaseEvidenceSource):
    """设计知识库"""
    source_type = EvidenceSource.DESIGN_KB

    def is_available(self):
        return os.path.isdir(KNOWLEDGE_DESIGN) and bool(list(Path(KNOWLEDGE_DESIGN).glob("*.md")))

    def search(self, error_item, features) -> list[EvidenceItem]:
        items = []
        if not self.is_available():
            return items
        for md_file in Path(KNOWLEDGE_DESIGN).glob("*.md"):
            content = md_file.read_text(encoding="utf-8")[:2000]
            for kw in features.search_keywords:
                if kw and kw in content:
                    items.append(EvidenceItem(
                        evidence_id=f"design_kb_{md_file.stem}",
                        source_type=EvidenceSource.DESIGN_KB, source_name=md_file.name,
                        matched_fields=["search_keywords"], relevance_level=RelevanceLevel.MEDIUM,
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_summary=f"设计知识库 [{md_file.stem}] 匹配 [{kw}]",
                        supports=["体验问题判断"],
                        limitations=["知识库条目可能未覆盖最新设计规范"],
                    ))
                    break
        return items


class HistoricalCaseRetriever(BaseEvidenceSource):
    """历史案例库"""
    source_type = EvidenceSource.HISTORICAL_CASE

    def is_available(self):
        return os.path.isdir(KNOWLEDGE_CASES) and bool(list(Path(KNOWLEDGE_CASES).glob("*.md")))

    def search(self, error_item, features) -> list[EvidenceItem]:
        items = []
        if not self.is_available():
            return items
        for md_file in Path(KNOWLEDGE_CASES).glob("*.md"):
            content = md_file.read_text(encoding="utf-8")[:2000]
            for kw in features.search_keywords:
                if kw and kw in content:
                    items.append(EvidenceItem(
                        evidence_id=f"case_{md_file.stem}",
                        source_type=EvidenceSource.HISTORICAL_CASE, source_name=md_file.name,
                        matched_fields=["search_keywords"], relevance_level=RelevanceLevel.MEDIUM,
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_summary=f"历史案例 [{md_file.stem}] 匹配 [{kw}]",
                        supports=["成效预估"],
                        limitations=["案例条件可能与当前场景不完全一致"],
                    ))
                    break
        return items


ALL_RETRIEVERS: list[BaseEvidenceSource] = [
    CustomerFeedbackRetriever(), TicketRetriever(), TrackingRetriever(),
    BusinessKnowledgeRetriever(), DesignKnowledgeRetriever(), HistoricalCaseRetriever(),
]


class EvidenceSourceAdapter:
    """多源证据检索编排器"""

    def retrieve_all(self, error_item, features) -> EvidenceSummary:
        all_items = []
        unavailable = []

        for retriever in ALL_RETRIEVERS:
            if retriever.is_available():
                all_items.extend(retriever.search(error_item, features))
            else:
                unavailable.append(retriever.source_type.value)

        strong = [i for i in all_items if i.relevance_level == RelevanceLevel.STRONG]
        medium = [i for i in all_items if i.relevance_level == RelevanceLevel.MEDIUM]
        weak = [i for i in all_items if i.relevance_level == RelevanceLevel.WEAK]

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
            conflict=EvidenceConflict(),
            sufficiency=suf,
        )

    def get_available_sources(self) -> list[str]:
        return [r.source_type.value for r in ALL_RETRIEVERS if r.is_available()]

    def get_unavailable_sources(self) -> list[str]:
        return [r.source_type.value for r in ALL_RETRIEVERS if not r.is_available()]
