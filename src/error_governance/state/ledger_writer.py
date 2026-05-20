"""治理台账 + 证据登记表写入"""

import os
import csv
from datetime import datetime
from error_governance.models.diagnosis_result import DiagnosisResult
from error_governance.config import STATE_LEDGER, STATE_EVIDENCE, STATUS_WAITING_HUMAN

LEDGER_FIELDS = ["error_id", "error_code", "error_message", "current_status", "diagnosis_report_path", "review_card_path", "evidence_total_count", "evidence_sufficiency_status", "evidence_conflict_flag", "human_review_result", "human_review_comment", "reviewer", "review_time"]

def _ensure_ledger():
    """确保台账文件存在且使用标准字段（覆盖模板中的旧字段名）"""
    need_create = not os.path.exists(STATE_LEDGER)
    if not need_create:
        # 检查已有文件的第一行是否包含所有标准字段
        with open(STATE_LEDGER, "r", encoding="utf-8-sig") as f:
            existing = f.readline().strip().split(",")
        if not all(k in existing for k in LEDGER_FIELDS):
            need_create = True
    if need_create:
        with open(STATE_LEDGER, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(LEDGER_FIELDS)

def _read_ledger_fieldnames() -> list[str]:
    """读取已有台账的字段名"""
    _ensure_ledger()
    with open(STATE_LEDGER, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fns = list(reader.fieldnames or [])
        return fns if fns else LEDGER_FIELDS


def write_diagnosis(d: DiagnosisResult):
    _ensure_ledger()
    fields = _read_ledger_fieldnames()
    row = {k: "" for k in fields}
    row.update({
        "error_id": d.governance_id,
        "error_code": d.error_input.error_code or "",
        "error_message": d.error_input.error_message,
        "current_status": STATUS_WAITING_HUMAN,
        "diagnosis_report_path": f"artifacts/diagnosis_reports/{d.governance_id}_report.md",
        "review_card_path": f"artifacts/review_cards/{d.governance_id}_review_card.md",
        "evidence_total_count": str(d.evidence.total_evidence_count),
        "evidence_sufficiency_status": "充足" if d.evidence.sufficiency.sufficient_for_diagnosis else "不足",
        "evidence_conflict_flag": str(d.evidence.conflict.has_conflict),
        "human_review_result": "", "human_review_comment": "", "reviewer": "", "review_time": "",
    })
    with open(STATE_LEDGER, "a", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=fields).writerow(row)

def update_review(gov_id: str, conclusion: str, reviewer: str, notes: str):
    rows = []
    fieldnames = []
    with open(STATE_LEDGER, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            if row.get("error_id") == gov_id:
                row["human_review_result"] = conclusion
                row["human_review_comment"] = notes
                row["reviewer"] = reviewer
                row["review_time"] = datetime.now().isoformat()
                row["current_status"] = "人工复核完成"
            rows.append(row)
    with open(STATE_LEDGER, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

EVIDENCE_FIELDS = ["evidence_id", "governance_id", "error_id", "source_type", "source_name", "matched_fields", "relevance_level", "confidence_level", "evidence_summary", "supports", "limitations", "conflict_flag", "created_time"]

def _ensure(path, fields):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(fields)

def _read_evidence_fieldnames() -> list[str]:
    if os.path.exists(STATE_EVIDENCE):
        with open(STATE_EVIDENCE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader.fieldnames or [])
    return EVIDENCE_FIELDS


def write_evidence(d: DiagnosisResult):
    fields = _read_evidence_fieldnames()
    _ensure(STATE_EVIDENCE, fields)
    with open(STATE_EVIDENCE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        for item in d.evidence.items:
            row = {k: "" for k in fields}
            row.update({"evidence_id": item.evidence_id, "governance_id": d.governance_id, "error_id": d.governance_id, "source_type": item.source_type.value, "source_name": item.source_name, "matched_fields": ";".join(item.matched_fields), "relevance_level": item.relevance_level.value, "confidence_level": item.confidence.value, "evidence_summary": item.evidence_summary, "supports": ";".join(item.supports), "limitations": ";".join(item.limitations), "conflict_flag": str(d.evidence.conflict.has_conflict), "created_time": datetime.now().isoformat()})
            w.writerow(row)
