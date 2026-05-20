"""运行日志存储 — run 级管理"""

import json
import os
from datetime import datetime
from error_governance.models.workflow_state import WorkflowState
from error_governance.config import STATE_RUNS


def init_run(run_id: str, input_file: str = "") -> dict:
    """创建 run 目录和元数据"""
    run_dir = os.path.join(STATE_RUNS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    meta = {
        "run_id": run_id,
        "input_file": input_file,
        "created_at": datetime.now().isoformat(),
        "status": "RUNNING",
        "total_items": 0,
        "completed_items": 0,
        "waiting_human_items": 0,
        "governance_ids": [],
    }
    _write_meta(run_id, meta)
    return meta


def _meta_path(run_id: str) -> str:
    return os.path.join(STATE_RUNS, run_id, "meta.json")


def _write_meta(run_id: str, meta: dict):
    with open(_meta_path(run_id), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, default=str)


def get_run_meta(run_id: str) -> dict:
    path = _meta_path(run_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def update_run_meta(run_id: str, **kwargs):
    meta = get_run_meta(run_id)
    meta.update(kwargs)
    _write_meta(run_id, meta)


def save_run_item(run_id: str, governance_id: str, state: WorkflowState):
    """在 run 目录下保存单个治理条目状态"""
    run_dir = os.path.join(STATE_RUNS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, f"{governance_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state.model_dump(), f, ensure_ascii=False, indent=2, default=str)


def load_run_item(run_id: str, governance_id: str) -> dict:
    path = os.path.join(STATE_RUNS, run_id, f"{governance_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_run_items(run_id: str) -> dict[str, dict]:
    """加载 run 下所有治理条目"""
    run_dir = os.path.join(STATE_RUNS, run_id)
    if not os.path.isdir(run_dir):
        return {}
    items = {}
    for f in os.listdir(run_dir):
        if f.endswith(".json") and f != "meta.json":
            gid = f.replace(".json", "")
            items[gid] = load_run_item(run_id, gid)
    return items


def add_governance_id(run_id: str, governance_id: str):
    meta = get_run_meta(run_id)
    if governance_id not in meta.get("governance_ids", []):
        meta.setdefault("governance_ids", []).append(governance_id)
        meta["total_items"] = len(meta["governance_ids"])
        _write_meta(run_id, meta)


def get_run_summary(run_id: str) -> dict:
    """获取 run 摘要（含各条目状态）"""
    meta = get_run_meta(run_id)
    items = load_run_items(run_id)

    summary = {
        "run_id": run_id,
        "status": meta.get("status", "UNKNOWN"),
        "input_file": meta.get("input_file", ""),
        "created_at": meta.get("created_at", ""),
        "total_items": len(items),
        "items": [],
    }

    for gid, data in items.items():
        log = data.get("run_log", {})
        # 兼容旧字段名 "status" 和新字段名 "item_status"
        item_status = data.get("item_status") or data.get("status", "")
        summary["items"].append({
            "governance_id": gid,
            "status": item_status,
            "error_code": log.get("error_id", ""),
            "steps_ok": sum(1 for k, v in log.items() if k.startswith("step_") and v),
            "needs_human": item_status == "待人工复核" and not data.get("human_review_completed"),
            "review_result": data.get("human_review_response", {}).get("conclusion", ""),
        })

    # 统计
    summary["waiting_human_count"] = sum(1 for i in summary["items"] if i["needs_human"])
    summary["reviewed_count"] = sum(1 for i in summary["items"] if i["review_result"])
    summary["diagnosed_count"] = sum(1 for i in summary["items"] if i["steps_ok"] >= 10)

    return summary


def list_runs() -> list[str]:
    os.makedirs(STATE_RUNS, exist_ok=True)
    runs = []
    for f in sorted(os.listdir(STATE_RUNS)):
        if os.path.isdir(os.path.join(STATE_RUNS, f)) and os.path.exists(_meta_path(f)):
            runs.append(f)
    return runs
