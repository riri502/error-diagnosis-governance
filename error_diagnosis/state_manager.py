"""状态管理 — 治理台账写入、证据登记表写入、状态更新"""

import os
import csv
from datetime import datetime
from error_diagnosis.models import DiagnosisReport
from error_diagnosis.config import STATE_LEDGER, STATE_EVIDENCE

LEDGER_FIELDS = [
    "error_id", "error_code", "error_message", "current_status",
    "diagnosis_report_path", "review_card_path",
    "evidence_total_count", "evidence_sufficiency_status", "evidence_conflict_flag",
    "human_review_result", "human_review_comment", "reviewer", "review_time",
]


def _ensure_ledger():
    """初始化台账文件（不存在则创建并写入表头）"""
    if not os.path.exists(STATE_LEDGER):
        with open(STATE_LEDGER, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(LEDGER_FIELDS)


def write_ledger_entry(report: DiagnosisReport, status: str):
    """写入治理台账条目"""
    _ensure_ledger()
    inp = report.error_input
    row = {
        "error_id": report.governance_id,
        "error_code": inp.error_code or "",
        "error_message": inp.error_message,
        "current_status": status,
        "diagnosis_report_path": os.path.join("artifacts/diagnosis_reports", f"{report.governance_id}_report.md"),
        "review_card_path": os.path.join("artifacts/review_cards", f"{report.governance_id}_review_card.md"),
        "evidence_total_count": str(report.evidence.total_evidence_count),
        "evidence_sufficiency_status": "充足" if report.evidence.sufficiency.sufficient_for_diagnosis else "不足",
        "evidence_conflict_flag": str(report.evidence.conflict.has_conflict),
        "human_review_result": "",
        "human_review_comment": "",
        "reviewer": "",
        "review_time": "",
    }
    with open(STATE_LEDGER, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writerow(row)


def update_ledger_review(governance_id: str, conclusion: str, reviewer: str, notes: str):
    """更新台账中的人工复核结论"""
    _ensure_ledger()
    rows = []
    with open(STATE_LEDGER, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("error_id") == governance_id:
                row["human_review_result"] = conclusion
                row["human_review_comment"] = notes
                row["reviewer"] = reviewer
                row["review_time"] = datetime.now().isoformat()
                row["current_status"] = "人工复核完成"
            rows.append(row)

    with open(STATE_LEDGER, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def update_ledger_status(governance_id: str, new_status: str):
    """更新台账条目状态"""
    _ensure_ledger()
    rows = []
    with open(STATE_LEDGER, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("error_id") == governance_id:
                row["current_status"] = new_status
            rows.append(row)

    with open(STATE_LEDGER, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


EVIDENCE_FIELDS = [
    "evidence_id", "governance_id", "error_id", "error_code",
    "source_type", "source_name", "matched_fields", "relevance_level",
    "confidence_level", "evidence_summary", "supports", "limitations",
    "conflict_flag", "conflict_type", "created_time",
]


def write_evidence_registry(report: DiagnosisReport):
    """写入证据登记表"""
    if not os.path.exists(STATE_EVIDENCE):
        with open(STATE_EVIDENCE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(EVIDENCE_FIELDS)

    with open(STATE_EVIDENCE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EVIDENCE_FIELDS)
        for item in report.evidence.items:
            writer.writerow({
                "evidence_id": item.evidence_id,
                "governance_id": report.governance_id,
                "error_id": report.governance_id,
                "error_code": report.error_input.error_code or "",
                "source_type": item.source_type.value,
                "source_name": item.source_name,
                "matched_fields": ";".join(item.matched_fields),
                "relevance_level": item.relevance_level.value,
                "confidence_level": item.confidence.value,
                "evidence_summary": item.evidence_summary,
                "supports": ";".join(item.supports),
                "limitations": ";".join(item.limitations),
                "conflict_flag": str(report.evidence.conflict.has_conflict),
                "conflict_type": report.evidence.conflict.conflict_type,
                "created_time": datetime.now().isoformat(),
            })
