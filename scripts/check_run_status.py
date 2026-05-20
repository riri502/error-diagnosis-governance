#!/usr/bin/env python3
"""查看当前运行状态

用法:
  python scripts/check_run_status.py --run-id RUN_001
  python scripts/check_run_status.py                  # 列出所有 run

输出:
  - 当前 run 的处理进度
  - 哪些条目已生成诊断报告
  - 哪些条目等待人工确认
  - 需要用户确认哪些问题
  - 人工确认文件路径
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from error_governance.state.run_store import (
    list_runs, get_run_meta, get_run_summary, load_run_items,
)
from error_governance.utils.csv_utils import read_csv
from error_governance.config import STATE_LEDGER


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="查看运行状态")
    parser.add_argument("--run-id", help="运行批次 ID（不指定则列出所有）")
    args = parser.parse_args()

    if args.run_id:
        _show_run_detail(args.run_id)
    else:
        _list_all_runs()


def _list_all_runs():
    runs = list_runs()
    if not runs:
        print("📭 暂无运行记录")
        return

    print(f"{'Run ID':<20} {'状态':<20} {'条目':>6} {'进度':>10}")
    print("-" * 60)
    for rid in runs:
        meta = get_run_meta(rid)
        summary = get_run_summary(rid)
        total = summary.get("total_items", meta.get("total_items", 0))
        reviewed = summary.get("reviewed_count", 0)
        progress = f"{reviewed}/{total}" if total else "-"
        print(f"{rid:<20} {meta.get('status','?'):<20} {total:>6} {progress:>10}")


def _show_run_detail(run_id: str):
    meta = get_run_meta(run_id)
    if not meta:
        print(f"❌ Run 不存在: {run_id}")
        return

    summary = get_run_summary(run_id)

    print("=" * 60)
    print(f"  Run: {run_id}")
    print(f"  状态: {meta.get('status', 'UNKNOWN')}")
    print(f"  输入: {meta.get('input_file', 'N/A')}")
    print(f"  创建时间: {meta.get('created_at', 'N/A')}")
    print(f"  总条目: {summary.get('total_items', 0)}")
    print(f"  已诊断: {summary.get('diagnosed_count', 0)}")
    print(f"  等待人工确认: {summary.get('waiting_human_count', 0)}")
    print(f"  已复核: {summary.get('reviewed_count', 0)}")
    print("=" * 60)

    items = summary.get("items", [])
    if not items:
        print("\n📭 无条目记录")
        return

    # 分类展示
    waiting = [i for i in items if i["needs_human"]]
    reviewed = [i for i in items if i["review_result"]]
    failed = [i for i in items if i["steps_ok"] < 10 and not i["needs_human"]]

    if waiting:
        print(f"\n⏸  等待人工确认 ({len(waiting)} 条):")
        print("-" * 60)
        for item in waiting:
            gid = item["governance_id"]
            ec = item.get("error_code", "?")
            print(f"  {gid} | 错误码: {ec} | 步骤: {item['steps_ok']}/11")
            # 检查问题卡和报告
            q_path = os.path.join(PROJECT_ROOT, "artifacts", "human_questions", f"{gid}_question.md")
            r_path = os.path.join(PROJECT_ROOT, "artifacts", "diagnosis_reports", f"{gid}_report.md")
            if os.path.exists(q_path):
                print(f"    问题卡: artifacts/human_questions/{gid}_question.md")
            if os.path.exists(r_path):
                print(f"    诊断报告: artifacts/diagnosis_reports/{gid}_report.md")

        # 批量问题卡
        batch_q = os.path.join(PROJECT_ROOT, "artifacts", "human_questions", f"{run_id}_batch_question.md")
        if os.path.exists(batch_q):
            print(f"\n  📄 批量问题卡: artifacts/human_questions/{run_id}_batch_question.md")

    if reviewed:
        print(f"\n✅ 已复核 ({len(reviewed)} 条):")
        print("-" * 60)
        for item in reviewed:
            print(f"  {item['governance_id']}: {item['review_result']}")

    if failed:
        print(f"\n❌ 诊断未完成 ({len(failed)} 条):")
        print("-" * 60)
        for item in failed:
            print(f"  {item['governance_id']}: 仅 {item['steps_ok']}/11 步骤通过")

    print(f"\n💡 继续流程:")
    print(f"   python scripts/resume_pipeline.py --run-id {run_id} --review-input <path>")


if __name__ == "__main__":
    main()
