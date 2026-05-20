"""工作流状态持久化"""

import json
import os
from error_governance.config import STATE_RUNS


def save(state_dict: dict, run_id: str):
    os.makedirs(STATE_RUNS, exist_ok=True)
    path = os.path.join(STATE_RUNS, f"{run_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state_dict, f, ensure_ascii=False, indent=2, default=str)


def load(run_id: str) -> dict:
    path = os.path.join(STATE_RUNS, f"{run_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
