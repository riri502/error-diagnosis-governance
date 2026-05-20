"""问题池写入 — 根据 human_review_result / evidence_review_result 分流

映射规则:
  human_review_result → 治理候选池 / 规则修正池 / 暂未复现池 / ...
  evidence_review_result → 证据不足池 / 证据冲突池 / 埋点缺口池 / ...
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from error_governance.config import STATE_ISSUE_POOLS


# ── 人工诊断结论 → 问题池 ──

HUMAN_REVIEW_POOL_MAP = {
    "评估准确，进入治理":       ("治理候选池.md", ""),
    "评估基本准确，需调整建议":  ("治理候选池.md", "需调整建议"),
    "评估不准确":               ("规则修正池.md", ""),
    "条目暂未复现":             ("暂未复现池.md", ""),
    "条目无需优化":             ("无需优化归档.md", ""),
    "需补充信息":               ("待补充信息池.md", ""),
    "需产品确认":               ("产品确认池.md", ""),
    "需研发确认":               ("研发确认池.md", ""),
    "需补充埋点":               ("埋点缺口池.md", ""),
}

# ── 证据复核结论 → 问题池 ──

EVIDENCE_REVIEW_POOL_MAP = {
    "证据不足，暂不进入治理":        ("证据不足池.md", ""),
    "证据引用不准确，需重新检索":     ("规则修正池.md", "证据引用不准确"),
    "证据冲突，需产品 / 运营确认":    ("证据冲突池.md", ""),
    "埋点证据缺失，需补充埋点":       ("埋点缺口池.md", ""),
}


# ── 条目数据结构 ──

@dataclass
class PoolEntry:
    """问题池条目"""
    error_id: str = ""
    error_code: str = ""
    run_id: str = ""
    ai_summary: str = ""
    human_review_result: str = ""
    evidence_review_result: str = ""
    diagnosis_report_path: str = ""
    review_card_path: str = ""
    next_action: str = ""
    notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ── 写入函数 ──

def write_issue_to_pool(governance_id: str, conclusion: str, notes: str):
    """向后兼容的简化接口 — 单条写入"""
    entry = PoolEntry(
        error_id=governance_id,
        human_review_result=conclusion,
        notes=notes,
    )
    _write_to_pool(entry, conclusion, "")


def write_full_entry(entry: PoolEntry):
    """写入完整条目到问题池

    根据 human_review_result 写入主池，
    根据 evidence_review_result 可能写入附加池。
    """
    # 主池（基于人工诊断结论）
    _write_to_pool(entry, entry.human_review_result, entry.evidence_review_result)

    # 附加池（基于证据复核结论，仅在不重复时写入）
    if entry.evidence_review_result:
        evidence_pool = EVIDENCE_REVIEW_POOL_MAP.get(entry.evidence_review_result)
        if evidence_pool:
            ev_pool_file, ev_tag = evidence_pool
            # 如果证据池与主池不同，额外写入
            human_pool = HUMAN_REVIEW_POOL_MAP.get(entry.human_review_result, ("待评估池.md", ""))
            if ev_pool_file != human_pool[0]:
                _append_entry(entry, ev_pool_file, ev_tag)


def _write_to_pool(entry: PoolEntry, human_result: str, evidence_result: str = ""):
    """写入主问题池"""
    pool_info = HUMAN_REVIEW_POOL_MAP.get(human_result)
    if not pool_info:
        pool_file = "待评估池.md"
        tag = ""
    else:
        pool_file, tag = pool_info

    _append_entry(entry, pool_file, tag)


def _append_entry(entry: PoolEntry, pool_file: str, tag: str = ""):
    """追加一条结构化条目到问题池文件"""
    os.makedirs(STATE_ISSUE_POOLS, exist_ok=True)
    path = os.path.join(STATE_ISSUE_POOLS, pool_file)

    # 格式化条目
    md = _format_entry(entry, tag)

    # 如果文件不存在，创建并写入表头
    if not os.path.exists(path):
        _init_pool_file(path)

    with open(path, "a", encoding="utf-8") as f:
        f.write(md)


def _init_pool_file(path: str):
    """初始化问题池文件"""
    pool_name = os.path.splitext(os.path.basename(path))[0]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {pool_name}\n\n"
                f"进入条件: (见 rules/DOC-06_异常分流与问题池规则.md)\n"
                f"后续动作: (见 rules/DOC-07_人工复核结论与状态流转规则.md)\n\n"
                f"---\n\n")


def _format_entry(entry: PoolEntry, tag: str = "") -> str:
    """格式化单条问题池条目为 Markdown"""
    date_str = entry.timestamp[:10] if entry.timestamp else datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"### {entry.error_id}",
        f"- **日期**: {date_str}",
        f"- **error_code**: {entry.error_code or '(无)'}",
        f"- **run_id**: {entry.run_id or '(无)'}",
    ]
    if entry.ai_summary:
        lines.append(f"- **AI 诊断摘要**: {entry.ai_summary}")
    lines.append(f"- **人工结论**: {entry.human_review_result}")
    if entry.evidence_review_result:
        lines.append(f"- **证据复核结论**: {entry.evidence_review_result}")
    if entry.diagnosis_report_path:
        lines.append(f"- **诊断报告**: {entry.diagnosis_report_path}")
    if entry.review_card_path:
        lines.append(f"- **复核卡**: {entry.review_card_path}")
    if entry.next_action:
        lines.append(f"- **下一步动作**: {entry.next_action}")
    if entry.notes:
        lines.append(f"- **备注**: {entry.notes}")
    if tag:
        lines.append(f"- **标记**: ⚠️ {tag}")

    lines.append("")
    return "\n".join(lines) + "\n"


# ── 便利函数：从 HumanReviewResponse + Diagnosis 构建条目 ──

def build_entry_from_response(
    response,       # HumanReviewResponse
    diagnosis=None, # DiagnosisResult (optional, from run data)
    run_id: str = "",
) -> PoolEntry:
    """从 HumanReviewResponse 构建 PoolEntry"""
    return PoolEntry(
        error_id=response.error_id,
        error_code=response.error_code if hasattr(response, 'error_code') else "",
        run_id=run_id,
        ai_summary="",
        human_review_result=response.human_review_result,
        evidence_review_result=response.evidence_review_result,
        diagnosis_report_path=(
            f"artifacts/diagnosis_reports/{run_id}/{response.error_id}_diagnosis_report.md"
            if run_id else ""
        ),
        review_card_path=(
            f"artifacts/review_cards/{run_id}/{response.error_id}_review_card.md"
            if run_id else ""
        ),
        next_action=response.next_action if hasattr(response, 'next_action') else "",
        notes=response.human_review_comment if hasattr(response, 'human_review_comment') else "",
    )
