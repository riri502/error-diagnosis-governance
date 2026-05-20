#!/usr/bin/env python3
"""初始化项目状态 — 检查并创建所有必要的 state 文件、目录和问题池

用法:
  python scripts/init_project_state.py
"""

import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from error_governance.config import (
    DATA_INBOX, DATA_PROCESSED,
    ARTIFACTS_DIAGNOSIS, ARTIFACTS_REVIEW_CARDS, ARTIFACTS_HUMAN_QUESTIONS,
    STATE_LEDGER, STATE_EVIDENCE, STATE_ISSUE_POOLS, STATE_RUNS,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "state")

TEMPLATES = {
    "governance_ledger.csv": "governance_ledger_template.csv",
    "review_registry.csv": "review_registry_template.csv",
    "evidence_registry.csv": "evidence_registry_template.csv",
}

REQUIRED_POOLS = [
    "待评估池", "治理候选池", "暂未复现池", "无需优化归档",
    "待补充信息池", "规则修正池", "埋点缺口池",
    "证据不足池", "证据冲突池",
    "待补充上线信息池", "埋点口径待确认池", "延长观察周期池",
]

REQUIRED_DIRS = [
    DATA_INBOX, DATA_PROCESSED,
    ARTIFACTS_DIAGNOSIS, ARTIFACTS_REVIEW_CARDS, ARTIFACTS_HUMAN_QUESTIONS,
    STATE_ISSUE_POOLS, STATE_RUNS,
]


def main():
    print("=" * 50)
    print("  报错诊断治理工具 — 初始化项目状态")
    print("=" * 50)

    # 1. 创建必要目录
    print("\n[1/4] 检查必要目录...")
    for d in REQUIRED_DIRS:
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
            print(f"  ✅ 新建目录: {os.path.relpath(d, PROJECT_ROOT)}")
        else:
            print(f"  ✓  已存在: {os.path.relpath(d, PROJECT_ROOT)}")

    # 2. 检查台账和登记表
    print("\n[2/4] 检查台账与登记表...")
    for target_name, template_name in TEMPLATES.items():
        target_path = os.path.join(PROJECT_ROOT, "state", target_name)
        template_path = os.path.join(TEMPLATE_DIR, template_name)

        if not os.path.exists(target_path):
            if os.path.exists(template_path):
                shutil.copy(template_path, target_path)
                print(f"  ✅ 从模板创建: state/{target_name}")
            else:
                print(f"  ⚠️  模板缺失: {template_name}，跳过")
        else:
            print(f"  ✓  已存在: state/{target_name}")

    # 3. 检查问题池
    print("\n[3/4] 检查问题池...")
    for pool_name in REQUIRED_POOLS:
        pool_file = os.path.join(STATE_ISSUE_POOLS, f"{pool_name}.md")
        if not os.path.exists(pool_file):
            with open(pool_file, "w", encoding="utf-8") as f:
                f.write(f"# {pool_name}\n\n进入条件: (待补充)\n后续动作: (待补充)\n")
            print(f"  ✅ 新建问题池: {pool_name}")
        else:
            print(f"  ✓  已存在: {pool_name}")

    # 4. 检查 artifacts 子目录
    print("\n[4/4] 检查 artifacts 子目录...")
    for sub in ["diagnosis_reports", "review_cards", "human_questions",
                "solution_packages", "copy_packages", "review_reports", "monthly_reports"]:
        d = os.path.join(PROJECT_ROOT, "artifacts", sub)
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)

    # .gitkeep
    for d in [DATA_INBOX, DATA_PROCESSED] + [
        os.path.join(PROJECT_ROOT, "knowledge", x)
        for x in ["business", "design", "cases_pending", "cases_confirmed"]
    ]:
        if os.path.isdir(d):
            gk = os.path.join(d, ".gitkeep")
            if not os.path.exists(gk):
                with open(gk, "w") as f:
                    pass

    print("\n" + "=" * 50)
    print("  初始化完成")
    print("=" * 50)
    print(f"\n  rules/ 目录未修改 ✓")


if __name__ == "__main__":
    main()
