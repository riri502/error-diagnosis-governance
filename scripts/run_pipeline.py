#!/usr/bin/env python3
"""启动一次自动诊断流程

用法:
  python scripts/run_pipeline.py --input data/inbox/errors.csv --run-id RUN_001
  python scripts/run_pipeline.py --input data/inbox/errors.csv --run-id RUN_001 --no-interact

作用:
  - 读取输入报错 → 校验字段 → SKILL-01-MVP 诊断
  - 生成诊断报告 + 人工复核卡 + 问题卡
  - 写入 governance_ledger / evidence_registry
  - 流程状态置为 WAITING_FOR_HUMAN
"""

import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from error_governance.adapters.file_input_adapter import FileInputAdapter
from error_governance.adapters.evidence_source_adapter import EvidenceSourceAdapter
from error_governance.pipeline.orchestrator import PipelineOrchestrator
from error_governance.state.run_store import init_run, update_run_meta, get_run_summary
from error_governance.config import ARTIFACTS_RUN_LOGS
from error_governance.human_gate.question_builder import build_batch_question_file


def main():
    parser = argparse.ArgumentParser(description="启动报错诊断流程")
    parser.add_argument("--input", required=True, help="报错 CSV 文件路径")
    parser.add_argument("--run-id", required=True, help="运行批次 ID，如 RUN_001")
    parser.add_argument("--no-interact", action="store_true", help="非交互模式")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 文件不存在: {args.input}")
        sys.exit(1)

    print("=" * 60)
    print(f"  报错诊断流程 — {args.run_id}")
    print(f"  输入: {args.input}")
    print(f"  时间: {datetime.now().isoformat()}")
    print("=" * 60)

    # Phase 0: 数据源状态
    es = EvidenceSourceAdapter()
    avail = es.get_available_sources()
    unavail = es.get_unavailable_sources()
    print(f"\n🔌 可用数据源: {', '.join(avail) if avail else '无'}")
    if unavail:
        print(f"⚠️  不可用数据源: {', '.join(unavail)}（将标记 unavailable_sources）")

    # 初始化 run
    meta = init_run(args.run_id, args.input)
    print(f"\n📋 Run 已创建: {args.run_id}")

    # 读取报错
    adapter = FileInputAdapter()
    read_result = adapter.read(args.input)
    if not read_result.success:
        print(f"❌ 读取失败: {read_result.error_message}")
        update_run_meta(args.run_id, status="FAILED")
        return

    # 输出标准化 CSV
    standardized_path = adapter.write_standardized(read_result, args.run_id)
    print(f"📄 标准化输出: {standardized_path}")

    errors = read_result.errors
    print(f"📊 有效: {len(errors)} 条, 阻断: {read_result.blocked_rows_count} 条, 警告: {len(read_result.warnings)} 条")

    if read_result.warnings:
        for w in read_result.warnings[:5]:
            print(f"  ⚠️  {w.get('error_id','?')} | {w.get('field','')}: {w.get('warning','')[:80]}")
        if len(read_result.warnings) > 5:
            print(f"  ... 共 {len(read_result.warnings)} 条警告")

    if not errors:
        print("⚠️ 无有效报错条目")
        update_run_meta(args.run_id, status="EMPTY")
        return
    print()

    # 逐条诊断
    orch = PipelineOrchestrator()
    results = []
    for i, err in enumerate(errors):
        print(f"[{i+1}/{len(errors)}] {err.error_message[:60]}...")
        result = orch.run(err, run_id=args.run_id)
        results.append(result)

        if result.success:
            print(f"  ✅ {result.governance_id} | {result.diagnosis.priority.priority.value}({result.diagnosis.priority.total_score}分) | {result.diagnosis.recommended_path.value}")
            print(f"     报告: {result.report_path}")
            print(f"     复核卡: {result.review_card_path}")
            print(f"     RunLog: {result.run_log_path}")
            print(f"     问题卡: {result.question_path}")
        else:
            print(f"  ❌ Step {result.blocked_at}: {result.block_reason}")

    # 生成汇总问题卡（供人工批量回复）
    batch_question_path = build_batch_question_file(
        args.run_id, results, args.input,
    )

    # 生成 run_summary.md
    run_summary_path = _write_run_summary(args.run_id, results, batch_question_path)

    # 更新 run 状态
    success_count = sum(1 for r in results if r.success)
    update_run_meta(args.run_id,
                    status="WAITING_FOR_HUMAN",
                    total_items=len(errors),
                    waiting_human_items=success_count,
    )

    # 输出摘要
    summary = get_run_summary(args.run_id)
    print(f"\n{'='*60}")
    print(f"  诊断完成")
    print(f"  成功: {success_count}/{len(errors)}")
    print(f"  状态: WAITING_FOR_HUMAN")
    print(f"  批量问题卡: {batch_question_path}")
    print(f"  Run 摘要: {run_summary_path}")
    print(f"{'='*60}")

    if not args.no_interact:
        print(f"\n⏸  流程已暂停，等待人工复核。")
        print(f"   请在 {batch_question_path} 中填写复核结论后执行:")
        print(f"   python scripts/resume_pipeline.py --run-id {args.run_id} --review-input <path>")


def _write_run_summary(run_id: str, results: list, question_path: str) -> str:
    """生成 Run 级别摘要 → artifacts/run_logs/{run_id}/run_summary.md"""
    run_dir = os.path.join(ARTIFACTS_RUN_LOGS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, "run_summary.md")

    success = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    lines = [
        f"# Run Summary — {run_id}",
        f"时间: {datetime.now().isoformat()}",
        f"总条目: {len(results)} | 成功: {len(success)} | 失败: {len(failed)}",
        "",
        "## 各条目诊断结果",
        "",
        "| error_id | 分类 | 优先级 | 路径 | 证据 | 置信度 |",
        "|---|---|---|---|---|---|",
    ]
    for r in success:
        d = r.diagnosis
        lines.append(
            f"| {r.governance_id} | {d.features.major_category}/{d.features.minor_category} | "
            f"{d.priority.priority.value}({d.priority.total_score}) | {d.recommended_path.value} | "
            f"{d.evidence.total_evidence_count}条 | {d.confidence_score:.0%} |"
        )
    for r in failed:
        lines.append(f"| {r.governance_id} | ❌ Step {r.blocked_at} | — | — | — | — |")

    lines += [
        "",
        "## 产出物",
        f"- 问题卡: {question_path}",
        f"- 诊断报告: artifacts/diagnosis_reports/{run_id}/",
        f"- 复核卡: artifacts/review_cards/{run_id}/",
        f"- Run 日志: artifacts/run_logs/{run_id}/",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


if __name__ == "__main__":
    main()
