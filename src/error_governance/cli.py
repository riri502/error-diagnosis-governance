#!/usr/bin/env python3
"""报错诊断治理工具 — CLI 入口

用法:
  python3 -m error_governance.cli data/inbox/errors.csv    # 文件输入
  python3 -m error_governance.cli --interactive             # 交互模式
  python3 -m error_governance.cli --no-interact             # 非交互（跳过人工确认）
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from error_governance.adapters.file_input_adapter import FileInputAdapter
from error_governance.adapters.evidence_source_adapter import EvidenceSourceAdapter
from error_governance.pipeline.orchestrator import PipelineOrchestrator
from error_governance.human_gate.response_parser import parse, CONCLUSIONS
from error_governance.human_gate.review_applier import apply_review
from error_governance.state.issue_pool_writer import write_issue_to_pool
from error_governance.config import DATA_INBOX


def print_banner():
    print("""
╔══════════════════════════════════════╗
║  报错诊断治理工具 (Error Diagnosis)  ║
║  Phase 0-3: 最小诊断主链 + 人工复核  ║
╚══════════════════════════════════════╝""")


def print_run_status(result):
    log = result.state.run_log if result.state else None
    if not log:
        return
    print(f"\n{'─'*45}")
    print(f"治理条目: {result.governance_id} | 状态: {log.current_status}")
    for i, attr in enumerate(["step_01_input_ok", "step_02_feature_ok", "step_04_evidence_search_ok", "step_05_evidence_relevance_ok", "step_06_experience_ok", "step_07_priority_ok", "step_08_effect_ok", "step_09_path_ok", "step_10_report_ok", "step_11_review_card_ok"], 1):
        ok = getattr(log, attr)
        print(f"  Step {i:02d}: {'✅' if ok else '❌'}")
    if log.evidence_sources_unavailable:
        print(f"  ⚠️ 不可用: {', '.join(log.evidence_sources_unavailable)}")
    if log.exception_type:
        print(f"  ⚠️ 异常: {log.exception_type}")
    print(f"  报告: {result.report_path}")
    print(f"  复核卡: {result.review_card_path}")
    print(f"{'─'*45}")


def print_review_prompt(result):
    d = result.diagnosis
    print(f"""
╔══════════════════════════════════════╗
║         ⚠️  需要人工复核确认         ║
╠══════════════════════════════════════╣
║ 条目: {result.governance_id}
║ 报错: {d.error_input.error_message[:50]}...
║ 诊断: {d.features.major_category}/{d.features.minor_category}
║ 优先级: {d.priority.priority.value}({d.priority.total_score}分)
║ 路径: {d.recommended_path.value}
║ 置信度: {d.confidence_score:.0%}
║ 证据: 共{d.evidence.total_evidence_count}条(强{d.evidence.strong_relevance_count}/中{d.evidence.medium_relevance_count})
╠══════════════════════════════════════╣
║ 回复序号选择复核结论:                ║
║ 1.评估准确  2.需调整  3.不准确      ║
║ 4.暂未复现  5.无需优化 6.需补充     ║
║ 7.产品确认  8.研发确认 9.需埋点     ║
║ 格式: <序号> <备注>                 ║
╚══════════════════════════════════════╝""")


def handle_review(result):
    print_review_prompt(result)
    try:
        raw = input(">>> ").strip()
        if not raw:
            print("⏭ 跳过，保留待复核状态")
            return
        resp, hint = parse(raw, result.governance_id)
        if resp is None:
            print(f"❌ {hint}")
            return handle_review(result)
        apply_review(resp)
        print(hint)
        write_issue_to_pool(result.governance_id, resp.conclusion, resp.notes)
    except (EOFError, KeyboardInterrupt):
        print("\n⏭ 跳过")


def process_file(filepath: str, interactive: bool = True):
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return
    print(f"📂 {filepath}")
    errors = FileInputAdapter().read_errors(filepath)
    print(f"📊 共 {len(errors)} 条报错")
    if not errors:
        return

    es = EvidenceSourceAdapter()
    avail = es.get_available_sources()
    unavail = es.get_unavailable_sources()
    if unavail:
        print(f"⚠️ 不可用数据源: {', '.join(unavail)}（标记 unavailable_sources）")

    orch = PipelineOrchestrator()
    for i, err in enumerate(errors):
        print(f"\n{'='*45}")
        print(f"[{i+1}/{len(errors)}] {err.error_message[:60]}...")
        result = orch.run(err)
        if not result.success:
            print(f"❌ Step {result.blocked_at}: {result.block_reason}")
            continue
        print_run_status(result)
        if result.needs_human and interactive:
            handle_review(result)
        elif result.needs_human:
            print("⚠️ 需要人工复核（非交互模式跳过）")


def interactive_mode():
    print("📝 交互模式 (Ctrl+C 退出)\n")
    from error_governance.models.error_item import ErrorItem
    try:
        msg = input("报错提示: ").strip()
        if not msg:
            print("❌ 不能为空"); return
        code = input("错误码: ").strip()
        url = input("URL: ").strip()
        route = input("路由: ").strip()
        trigger = input("触发场景: ").strip()
        cnt = input("报错次数: ").strip()
        err = ErrorItem(error_code=code, error_message=msg, url=url, page_route=route, trigger_scenario=trigger, error_count=int(cnt) if cnt.isdigit() else 1)
        result = PipelineOrchestrator().run(err)
        if not result.success:
            print(f"❌ {result.block_reason}"); return
        print_run_status(result)
        handle_review(result)
    except (EOFError, KeyboardInterrupt):
        print("\n👋")


def main():
    import argparse
    p = argparse.ArgumentParser(description="报错诊断治理工具")
    p.add_argument("file", nargs="?", help="报错 CSV 文件路径")
    p.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    p.add_argument("--no-interact", action="store_true", help="跳过人工确认")
    args = p.parse_args()

    print_banner()
    if args.interactive:
        interactive_mode()
    elif args.file:
        process_file(args.file, interactive=not args.no_interact)
    else:
        inbox = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "inbox")
        csvs = [f for f in os.listdir(inbox) if f.endswith(".csv")] if os.path.isdir(inbox) else []
        if csvs:
            process_file(os.path.join(inbox, csvs[0]), interactive=not args.no_interact)
        else:
            p.print_help()


if __name__ == "__main__":
    main()
