"""Step 03-04: 检索关键词生成 + 多源证据检索"""

from error_governance.models.evidence import EvidenceSummary
from error_governance.adapters.evidence_source_adapter import EvidenceSourceAdapter

_adapter = EvidenceSourceAdapter()


def retrieve(error_item, features) -> EvidenceSummary:
    """执行多源证据检索"""
    return _adapter.retrieve_all(error_item, features)


def get_available() -> list[str]:
    return _adapter.get_available_sources()


def get_unavailable() -> list[str]:
    return _adapter.get_unavailable_sources()
