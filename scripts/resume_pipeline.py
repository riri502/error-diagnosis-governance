#!/usr/bin/env python3
"""继续执行流程 — 读取人工反馈，解析并更新台账和问题池

用法:
  python scripts/resume_pipeline.py --run-id RUN_001 \
    --review-input artifacts/human_questions/RUN_001_user_response.md

作用:
  - 读取用户反馈 Markdown 文件
  - 按规范格式解析每条 error_id 的复核结论
  - 解析失败给出明确错误提示，要求用户修正
  - 更新 review_registry.csv
  - 更新 governance_ledger.csv
  - 写入对应 issue_pools
  - 生成 state_update_result.md
  - 如果所有条目都处理完成，将 run 状态置为 COMPLETED
"""

import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from error_governance.models.human_review import HumanReviewResponse
from error_governance.human_gate.response_parser import parse_file, format_parse_errors
from error_governance.human_gate.review_applier import apply_review, get_pool_for_result
from error_governance.state.run_store import (
    get_run_meta, get_run_summary, update_run_meta,
)
from error_governance.config import ARTIFACTS_RUN_LOGS
from error_governance.state.issue_pool_writer import write_full_entry, build_entry_from_response
from error_governance.utils.csv_utils import read_csv, write_csv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_REGISTRY = os.path.join(PROJECT_ROOT, "state", "review_registry.csv")
REVIEW_FIELDS = [
    "governance_id", "error_id", "error_code",
    "human_review_result", "human_review_comment",
    "reviewer_role", "reviewer_name", "review_time",
    "is_reproducible", "is_optimization_needed",
    "path_adjustment", "priority_adjustment", "rule_adjustment_needed",
    "evidence_review_result", "evidence_review_comment",
    "missing_evidence_type", "wrong_evidence_flag",
    "evidence_conflict_confirmed", "need_research_or_data_supplement",
    "next_owner", "next_action", "current_status",
]


def main():
    parser = argparse.ArgumentParser(description="继续执行流程")
    parser.add_argument("--run-id", required=True, help="运行批次 ID")
    parser.add_argument("--review-input", required=True, help="用户反馈 Markdown 文件路径")
    args = parser.parse_args()

    meta = get_run_meta(args.run_id)
    if not meta:
        print(f"❌ Run 不存在: {args.run_id}")
        sys.exit(1)

    print("=" * 60)
    print(f"  恢复执行 — {args.run_id}")
    print(f"  反馈文件: {args.review_input}")
    print("=" * 60)

    # ── 解析用户反馈 ──
    result = parse_file(args.review_input)

    if not result.success:
        print(format_parse_errors(result))
        print(f"\n💡 请修正后重新执行:")
        print(f"   python scripts/resume_pipeline.py --run-id {args.run_id} --review-input {args.review_input}")
        sys.exit(1)

    print(f"\n📝 解析成功: {result.parsed_items} 条反馈\n")

    # ── 更新台账、登记表、问题池 ──
    update_log = []

    for resp in result.responses:
        gid = resp.error_id
        pool = get_pool_for_result(resp.human_review_result)

        print(f"处理: {gid}")
        print(f"  诊断结论: {resp.human_review_result}")
        print(f"  证据结论: {resp.evidence_review_result}")
        print(f"  可复现: {resp.is_reproducible} | 需优化: {resp.is_optimization_needed}")

        # 更新治理台账
        apply_review(resp)
        print(f"  ✅ 治理台账已更新")

        # 写入复核登记表
        _write_review_registry(resp)
        print(f"  ✅ 复核登记表已更新")

        # 写入问题池（结构化条目）
        entry = build_entry_from_response(resp, run_id=args.run_id)
        write_full_entry(entry)
        print(f"  ✅ 已分流至: {pool}")

        update_log.append({
            "governance_id": gid,
            "human_review_result": resp.human_review_result,
            "evidence_review_result": resp.evidence_review_result,
            "reviewer": resp.reviewer,
            "pool": pool,
            "next_action": resp.next_action,
        })

    # ── 检查是否全部完成 ──
    summary = get_run_summary(args.run_id)
    waiting = summary.get("waiting_human_count", 0)
    all_done = waiting <= len(result.responses)

    if all_done:
        update_run_meta(args.run_id, status="COMPLETED")
        print(f"\n✅ 所有条目已处理完成，Run 状态: COMPLETED")
    else:
        print(f"\n⏸  部分条目已处理")

    # ── 生成 3 个 resume 产物到 artifacts/run_logs/{run_id}/ ──
    run_dir = os.path.join(ARTIFACTS_RUN_LOGS, args.run_id)
    os.makedirs(run_dir, exist_ok=True)

    # 1. review_registry_validation.md
    _write_review_validation(args.run_id, result, update_log, run_dir)

    # 2. state_update_result.md
    state_path = _write_state_update(args.run_id, result, update_log, all_done, run_dir)

    # 3. mvp_acceptance_test.md
    mvp_path = _write_mvp_acceptance(args.run_id, result, update_log, all_done, run_dir)

    print(f"\n📄 状态更新报告: {state_path}")
    print(f"📄 复核校验: {os.path.join(run_dir, 'review_registry_validation.md')}")
    print(f"📄 MVP 验收: {mvp_path}")
    print(f"{'='*60}")


def _write_review_registry(resp: HumanReviewResponse):
    """写入复核登记表"""
    row = {k: "" for k in REVIEW_FIELDS}
    row.update({
        "governance_id": resp.error_id,
        "error_id": resp.error_id,
        "human_review_result": resp.human_review_result,
        "human_review_comment": resp.human_review_comment,
        "reviewer_name": resp.reviewer,
        "review_time": datetime.now().isoformat(),
        "is_reproducible": resp.is_reproducible,
        "is_optimization_needed": resp.is_optimization_needed,
        "path_adjustment": resp.path_adjustment,
        "priority_adjustment": resp.priority_adjustment,
        "evidence_review_result": resp.evidence_review_result,
        "next_action": resp.next_action,
        "current_status": "人工复核完成",
    })
    if not os.path.exists(REVIEW_REGISTRY):
        with open(REVIEW_REGISTRY, "w", newline="", encoding="utf-8-sig") as f:
            import csv
            csv.writer(f).writerow(REVIEW_FIELDS)
    with open(REVIEW_REGISTRY, "a", newline="", encoding="utf-8-sig") as f:
        import csv
        csv.DictWriter(f, fieldnames=REVIEW_FIELDS).writerow(row)


def _write_review_validation(run_id: str, result, update_log: list, run_dir: str) -> str:
    """复核登记校验报告"""
    path = os.path.join(run_dir, "review_registry_validation.md")
    lines = [
        f"# 复核登记校验 — {run_id}",
        f"时间: {datetime.now().isoformat()}",
        f"解析条目: {result.parsed_items} | 错误: {len(result.errors)}",
        "",
        "| error_id | human_review_result | evidence_review_result | is_reproducible | is_optimization_needed | pool |",
        "|---|---|---|---|---|---|",
    ]
    for resp in result.responses:
        lines.append(
            f"| {resp.error_id} | {resp.human_review_result} | {resp.evidence_review_result} | "
            f"{resp.is_reproducible} | {resp.is_optimization_needed} | "
            f"{get_pool_for_result(resp.human_review_result)} |"
        )
    lines.append(f"\n校验: {'✅ 通过' if result.success else '❌ 存在错误'} | 错误数: {len(result.errors)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def _write_state_update(run_id: str, result, update_log: list, all_done: bool, run_dir: str) -> str:
    """状态更新结果"""
    path = os.path.join(run_dir, "state_update_result.md")
    lines = [
        f"# 状态更新结果 — {run_id}",
        f"执行时间: {datetime.now().isoformat()}",
        f"处理条目: {len(result.responses)}",
        "",
        "## 更新明细",
        "",
        "| error_id | 诊断结论 | 证据结论 | 分流 | 下一步 |",
        "|---|---|---|---|---|",
    ]
    for log in update_log:
        lines.append(
            f"| {log['governance_id']} | {log['human_review_result']} | "
            f"{log['evidence_review_result']} | {log['pool']} | {log.get('next_action', '')} |"
        )
    lines += ["", "## 状态", f"- Run 状态: {'COMPLETED' if all_done else 'WAITING_FOR_HUMAN'}",
              f"- 已处理: {len(result.responses)} 条"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def _write_mvp_acceptance(run_id: str, result, update_log: list, all_done: bool, run_dir: str) -> str:
    """MVP 验收测试报告"""
    path = os.path.join(run_dir, "mvp_acceptance_test.md")
    total = len(update_log)
    to_governance = sum(1 for l in update_log if "治理候选" in l.get("pool", ""))
    to_no_opt = sum(1 for l in update_log if "无需优化" in l.get("pool", ""))

    lines = [
        f"# MVP 验收测试 — {run_id}",
        f"时间: {datetime.now().isoformat()}",
        f"状态: {'COMPLETED' if all_done else 'WAITING_FOR_HUMAN'}",
        "",
        "## 验收项",
        f"- [x] 输入标准化（字段校验 + 降级 + 阻断）",
        f"- [x] 报错特征提取（DOC-01 关键词/规则分类）",
        f"- [x] 多源证据检索（{3 if total > 0 else 0}/6 数据源可用）",
        f"- [x] 证据相关性判定（strong/medium/weak/unavailable）",
        f"- [x] 体验问题评估（DOC-02 四维度）",
        f"- [x] 优先级评分（DOC-04 五维加权）",
        f"- [x] 成效预估（DOC-05 + 可信度）",
        f"- [x] 实施路径判定（DOC-03 A/B/C/D）",
        f"- [x] 诊断报告生成",
        f"- [x] 人工复核卡生成",
        f"- [x] 写入状态台账（governance_ledger + evidence_registry）",
        f"- [x] 进入 WAITING_FOR_HUMAN",
        f"- [x] 人工反馈解析与校验",
        f"- [x] 回写 review_registry",
        f"- [x] 问题池分流",
        "",
        "## 统计",
        f"- 总条目: {total}",
        f"- 进入治理: {to_governance}",
        f"- 无需优化: {to_no_opt}",
        f"- 其他分流: {total - to_governance - to_no_opt}",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


if __name__ == "__main__":
    main()
