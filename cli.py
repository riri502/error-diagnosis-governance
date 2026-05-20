#!/usr/bin/env python3
"""报错诊断治理工具 — CLI 入口

支持两种输入：
1. 本地文件: python cli.py data/inbox/errors.csv
2. 交互模式: python cli.py --interactive

执行流程：
  读取报错 → 标准化 → 分类 → 证据检索 → 体验评估 →
  优先级评分 → 成效预估 → 路径判定 → 报告生成 →
  人工复核卡 → 等待人工确认 → 回写台账
"""

import os
import sys
import argparse
from datetime import datetime

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from error_diagnosis.pipeline import load_errors_from_csv, run_diagnosis, PipelineResult
from error_diagnosis.retrievers import get_available_sources, get_unavailable_sources
from error_diagnosis.state_manager import update_ledger_review


def print_banner():
    print("""
╔══════════════════════════════════════════════╗
║     报错诊断治理工具 (Error Diagnosis)       ║
║     Phase 0-3: 最小诊断主链 + 人工复核闭环    ║
╚══════════════════════════════════════════════╝
""")


def print_run_status(result: PipelineResult):
    """打印运行状态摘要"""
    log = result.run_log
    if not log:
        return
    print(f"\n{'─'*50}")
    print(f"治理条目 ID: {result.governance_id}")
    print(f"状态: {log.current_status}")
    print(f"Step 01 输入标准化: {'✅' if log.step_01_input_ok else '❌'}")
    print(f"Step 02 特征提取:   {'✅' if log.step_02_feature_ok else '❌'}")
    print(f"Step 03 关键词生成: {'✅' if log.step_03_keyword_gen_ok else '❌'}")
    print(f"Step 04 证据检索:   {'✅' if log.step_04_evidence_search_ok else '❌'}")
    print(f"Step 05 证据相关性: {'✅' if log.step_05_evidence_relevance_ok else '❌'}")
    print(f"Step 06 体验评估:   {'✅' if log.step_06_experience_ok else '❌'}")
    print(f"Step 07 优先级评分: {'✅' if log.step_07_priority_ok else '❌'}")
    print(f"Step 08 成效预估:   {'✅' if log.step_08_effect_ok else '❌'}")
    print(f"Step 09 路径判定:   {'✅' if log.step_09_path_ok else '❌'}")
    print(f"Step 10 报告生成:   {'✅' if log.step_10_report_ok else '❌'}")
    print(f"Step 11 复核卡:     {'✅' if log.step_11_review_card_ok else '❌'}")

    if log.evidence_sources_available:
        print(f"可用数据源: {', '.join(log.evidence_sources_available)}")
    if log.evidence_sources_unavailable:
        print(f"不可用数据源: {', '.join(log.evidence_sources_unavailable)} ⚠️")
    if log.exception_type:
        print(f"异常类型: {log.exception_type}")

    print(f"\n诊断报告: {result.report_path}")
    print(f"复核卡:   {result.review_card_path}")
    print(f"{'─'*50}")


def print_review_prompt(result: PipelineResult):
    """打印人工复核问答卡片"""
    if not result.report:
        return

    r = result.report
    print(f"""
╔══════════════════════════════════════════════╗
║           ⚠️  需要人工复核确认               ║
╠══════════════════════════════════════════════╣
║ 治理条目: {result.governance_id}
║ 报错文案: {r.error_input.error_message[:50]}...
║ AI 诊断: {r.features.major_category}/{r.features.minor_category}
║ 优先级: {r.priority.priority.value} ({r.priority.total_score}分)
║ 路径: {r.recommended_path.value}
║ 置信度: {r.confidence_score:.0%}
║ 证据: 共{r.evidence.total_evidence_count}条（强{r.evidence.strong_relevance_count}/中{r.evidence.medium_relevance_count}/弱{r.evidence.weak_relevance_count}）
╠══════════════════════════════════════════════╣
║ 请回复你的复核结论（选择一项）：              ║
║   1. 评估准确，进入治理                       ║
║   2. 评估基本准确，需调整建议                  ║
║   3. 评估不准确                              ║
║   4. 条目暂未复现                            ║
║   5. 条目无需优化                            ║
║   6. 需补充信息                              ║
║   7. 需产品确认                              ║
║   8. 需研发确认                              ║
║   9. 需补充埋点                              ║
║                                              ║
║ 格式: <序号> <备注>(可选)                     ║
║ 示例: 1 优先级可从P1调整为P0                  ║
╚══════════════════════════════════════════════╝
""")


def handle_human_review(result: PipelineResult):
    """处理人工复核交互"""
    REVIEW_OPTIONS = {
        "1": "评估准确，进入治理",
        "2": "评估基本准确，需调整建议",
        "3": "评估不准确",
        "4": "条目暂未复现",
        "5": "条目无需优化",
        "6": "需补充信息",
        "7": "需产品确认",
        "8": "需研发确认",
        "9": "需补充埋点",
    }

    print_review_prompt(result)

    try:
        raw = input(">>> ").strip()
        if not raw:
            print("⏭ 跳过人工复核，条目保留在待复核状态")
            return

        parts = raw.split(maxsplit=1)
        choice = parts[0]
        notes = parts[1] if len(parts) > 1 else ""

        if choice not in REVIEW_OPTIONS:
            print(f"❌ 无效选项: {choice}，请选择 1-9")
            return handle_human_review(result)

        conclusion = REVIEW_OPTIONS[choice]
        update_ledger_review(
            result.governance_id,
            conclusion=conclusion,
            reviewer="CLI交互用户",
            notes=notes,
        )

        print(f"\n✅ 复核结论已记录: {conclusion}")
        if notes:
            print(f"   备注: {notes}")

        # 分流提示
        if choice in ["3", "4", "5", "6", "7", "8", "9"]:
            pool_map = {
                "3": "规则修正池", "4": "暂未复现池", "5": "无需优化归档",
                "6": "待补充信息池", "7": "产品确认池", "8": "研发确认池",
                "9": "埋点缺口池",
            }
            print(f"   → 已分流至: {pool_map.get(choice, '对应问题池')}")
        elif choice in ["1", "2"]:
            print(f"   → 已进入: 治理候选池")

    except (EOFError, KeyboardInterrupt):
        print("\n⏭ 人工复核跳过")


def process_file(filepath: str, interactive: bool = True):
    """处理报错文件"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    print(f"📂 读取报错文件: {filepath}")
    errors = load_errors_from_csv(filepath)
    print(f"📊 共加载 {len(errors)} 条报错")

    if not errors:
        print("⚠️ 文件中无有效报错条目")
        return

    # 数据源状态
    available = get_available_sources()
    unavailable = get_unavailable_sources()
    if available:
        print(f"🔌 可用数据源: {', '.join(available)}")
    if unavailable:
        print(f"⚠️  不可用数据源: {', '.join(unavailable)}（将标记为 unavailable_sources）")

    # 逐条处理
    for i, error_input in enumerate(errors):
        print(f"\n{'='*50}")
        print(f"处理第 {i+1}/{len(errors)} 条: {error_input.error_message[:60]}...")

        # 检查是否需要人工确认的节点
        if error_input.error_message and not error_input.error_code:
            print(f"⚠️  缺少错误码，进入 WAITING_FOR_HUMAN 状态")
            if not interactive:
                continue

        result = run_diagnosis(error_input)

        if not result.success:
            print(f"❌ 诊断失败 (Step {result.blocked_at_step}): {result.block_reason}")
            continue

        print_run_status(result)

        if result.needs_human and interactive:
            handle_human_review(result)
        elif result.needs_human:
            print("⚠️  需要人工复核（非交互模式跳过）")
            print_review_prompt(result)


def interactive_mode():
    """交互模式：手动输入单条报错"""
    print("📝 交互模式：请输入报错信息（Ctrl+C 退出）\n")

    try:
        error_message = input("报错提示 (必填): ").strip()
        if not error_message:
            print("❌ 报错提示不能为空")
            return

        error_code = input("错误码 (可选): ").strip()
        url = input("URL (可选): ").strip()
        page_route = input("页面路由 (可选): ").strip()
        trigger = input("触发场景 (可选): ").strip()
        count_str = input("报错次数 (默认1): ").strip()

        error_input = __import__("error_diagnosis.models", fromlist=["ErrorInput"]).ErrorInput(
            error_code=error_code or "",
            error_message=error_message,
            url=url or "",
            page_route=page_route or "",
            trigger_scenario=trigger or "",
            error_count=int(count_str) if count_str.isdigit() else 1,
        )

        result = run_diagnosis(error_input)

        if not result.success:
            print(f"❌ 诊断失败: {result.block_reason}")
            return

        print_run_status(result)
        handle_human_review(result)

    except (EOFError, KeyboardInterrupt):
        print("\n👋 退出")


def main():
    parser = argparse.ArgumentParser(description="报错诊断治理工具 CLI")
    parser.add_argument("file", nargs="?", help="报错 CSV 文件路径")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--no-interact", action="store_true", help="非交互模式（跳过人工确认）")
    args = parser.parse_args()

    print_banner()

    # 预留 API Adapter 接口（不实现）
    # class APIAdapter:
    #     def fetch_errors(self) -> list[ErrorInput]: ...

    if args.interactive:
        interactive_mode()
    elif args.file:
        process_file(args.file, interactive=not args.no_interact)
    else:
        # 默认尝试 data/inbox/ 下第一个 CSV
        inbox = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "inbox")
        if os.path.isdir(inbox):
            csv_files = [f for f in os.listdir(inbox) if f.endswith(".csv")]
            if csv_files:
                filepath = os.path.join(inbox, csv_files[0])
                print(f"📂 自动检测到输入文件: {filepath}")
                process_file(filepath, interactive=not args.no_interact)
            else:
                print("📂 data/inbox/ 中无 CSV 文件，使用样本数据")
                sample = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "samples", "sample_errors.csv")
                process_file(sample, interactive=not args.no_interact)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
