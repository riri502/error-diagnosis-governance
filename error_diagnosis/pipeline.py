"""主 Pipeline — SKILL-01 11 步编排，含人工确认节点"""

import csv
import os
import uuid
from datetime import datetime
from typing import Optional, Callable

from error_diagnosis.config import (
    INPUT_FIELD_ALIASES, REQUIRED_FIELDS, STATUS_DIAGNOSING,
    STATUS_WAITING_HUMAN, LOW_CONFIDENCE_THRESHOLD, DATA_INBOX,
)
from error_diagnosis.models import (
    ErrorInput, DiagnosisReport, ReviewCard, RunLog,
    EvidenceSummary, PriorityLevel,
)
from error_diagnosis.classifiers import classify_error
from error_diagnosis.retrievers import retrieve_all_evidence, get_available_sources, get_unavailable_sources
from error_diagnosis.evaluators import evaluate_experience
from error_diagnosis.scorers import assess_priority, estimate_effect, determine_path
from error_diagnosis.reporters import generate_report, generate_review_card
from error_diagnosis.state_manager import write_ledger_entry, write_evidence_registry, update_ledger_review


class PipelineResult:
    """Pipeline 执行结果"""
    def __init__(self):
        self.success: bool = False
        self.needs_human: bool = False
        self.governance_id: str = ""
        self.report: Optional[DiagnosisReport] = None
        self.review_card: Optional[ReviewCard] = None
        self.run_log: Optional[RunLog] = None
        self.report_path: str = ""
        self.review_card_path: str = ""
        self.blocked_at_step: str = ""
        self.block_reason: str = ""
        self.error: Optional[str] = None


def load_errors_from_csv(filepath: str) -> list[ErrorInput]:
    """从 CSV 文件加载报错数据，自动识别字段别名（Step 01 的部分）"""
    errors = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # 建立别名映射
        header_map = {}
        for col in reader.fieldnames or []:
            col_clean = col.strip()
            for std_name, aliases in INPUT_FIELD_ALIASES.items():
                if col_clean == std_name or col_clean in aliases:
                    header_map[col_clean] = std_name
                    break
            if col_clean not in header_map:
                header_map[col_clean] = col_clean  # 保留原名

        for row in reader:
            mapped = {}
            for col, val in row.items():
                std = header_map.get(col.strip(), col.strip())
                mapped[std] = (val or "").strip()

            # 校验必填字段
            if not mapped.get("error_message"):
                continue  # 跳过无报错提示的行

            errors.append(ErrorInput(
                error_code=mapped.get("error_code", ""),
                error_message=mapped["error_message"],
                url=mapped.get("url", ""),
                page_route=mapped.get("page_route", ""),
                trigger_scenario=mapped.get("trigger_scenario", ""),
                error_count=int(mapped.get("error_count", "1") or "1"),
            ))
    return errors


def run_diagnosis(
    input: ErrorInput,
    human_callback: Optional[Callable[[DiagnosisReport, ReviewCard], dict]] = None,
) -> PipelineResult:
    """运行 SKILL-01 完整 11 步诊断流程

    Args:
        input: 报错输入
        human_callback: 人工确认回调（若为 None 且需要人工确认，则返回 needs_human=True）
    """
    result = PipelineResult()
    governance_id = f"GOV_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    result.governance_id = governance_id

    run_log = RunLog(run_id=governance_id, error_id=input.error_code or governance_id)
    run_log.current_status = STATUS_DIAGNOSING

    # ═══ Step 01: 输入标准化 ═══
    if not input.error_message:
        result.blocked_at_step = "01"
        result.block_reason = "报错提示为空，无法继续"
        result.run_log = run_log
        return result
    run_log.step_01_input_ok = True

    # ═══ Step 02: 报错特征提取 ═══
    features = classify_error(input)
    run_log.step_02_feature_ok = True

    # ═══ Step 03: 检索关键词生成 ═══
    run_log.step_03_keyword_gen_ok = True

    # ═══ Step 04: 多源证据检索 ═══
    evidence = retrieve_all_evidence(input, features)
    run_log.step_04_evidence_search_ok = True
    run_log.evidence_sources_available = get_available_sources()
    run_log.evidence_sources_unavailable = get_unavailable_sources()

    # ═══ Step 05: 证据相关性判定 ═══
    # 已在 retrieve_all_evidence 中进行相关性分级
    if evidence.total_evidence_count == 0:
        result.blocked_at_step = "05"
        result.block_reason = "所有数据源均不可用，无可用证据"
        run_log.exception_type = "无证据"
        result.run_log = run_log
        # 不阻断，继续走低置信评估
    run_log.step_05_evidence_relevance_ok = True

    # ═══ Step 06: 体验问题评估 ═══
    experience = evaluate_experience(input, features)
    run_log.step_06_experience_ok = True

    # ═══ Step 07: 优先级评分 ═══
    priority = assess_priority(input, features, evidence, experience)
    run_log.step_07_priority_ok = True

    # ═══ Step 08: 成效预估 ═══
    effect = estimate_effect(input, features, evidence, priority)
    run_log.step_08_effect_ok = True

    # ═══ Step 09: 实施路径判定 ═══
    path, path_rationale = determine_path(features, experience)
    run_log.step_09_path_ok = True

    # ═══ Step 10: 综合诊断报告生成 ═══
    conf_score = 0.5
    if evidence.sufficiency.sufficient_for_diagnosis:
        conf_score += 0.2
    if evidence.sufficiency.sufficient_for_priority_scoring:
        conf_score += 0.2
    if evidence.sufficiency.sufficient_for_effect_estimation:
        conf_score += 0.1

    report = DiagnosisReport(
        governance_id=governance_id,
        error_input=input,
        features=features,
        evidence=evidence,
        experience=experience,
        priority=priority,
        effect=effect,
        recommended_path=path,
        path_rationale=path_rationale,
        optimization_direction=_build_optimization_direction(features, experience),
        verification_plan=_build_verification_plan(features),
        confidence_score=conf_score,
    )
    report_path = generate_report(report, governance_id)
    result.report_path = report_path
    run_log.step_10_report_ok = True

    # ═══ Step 11: 人工复核卡生成 ═══
    review_card = ReviewCard(
        governance_id=governance_id,
        error_message=input.error_message,
        ai_summary=f"{features.major_category}/{features.minor_category} — {priority.priority.value}({priority.total_score}分)",
        recommended_path=path.value,
        priority=priority.priority.value,
        evidence_summary_text=f"共{evidence.total_evidence_count}条证据，强相关{evidence.strong_relevance_count}条",
        review_items=["证据相关性", "AI诊断准确性", "路径建议合理性", "优先级合理性"],
    )
    review_card_path = generate_review_card(report, governance_id)
    result.review_card_path = review_card_path
    run_log.step_11_review_card_ok = True

    # ═══ 写入台账和证据登记表 ═══
    write_ledger_entry(report, STATUS_WAITING_HUMAN)
    write_evidence_registry(report)

    # ═══ 低置信度检查 ═══
    if conf_score < LOW_CONFIDENCE_THRESHOLD:
        run_log.exception_type = "低置信"
        run_log.current_status = STATUS_WAITING_HUMAN
        result.needs_human = True
    else:
        run_log.current_status = STATUS_WAITING_HUMAN
        result.needs_human = True  # 始终需要人工复核

    result.success = True
    result.report = report
    result.review_card = review_card
    result.run_log = run_log

    # ═══ 人工确认节点 ═══
    if human_callback:
        human_result = human_callback(report, review_card)
        # 回写人工结论
        update_ledger_review(
            governance_id,
            conclusion=human_result.get("conclusion", ""),
            reviewer=human_result.get("reviewer", ""),
            notes=human_result.get("notes", ""),
        )
        result.needs_human = False

    return result


def _build_optimization_direction(features, experience) -> str:
    """构建初步优化方向"""
    parts = []
    major = features.major_category
    if "校验" in major:
        parts.append("校验时机前置（输入失焦/提交前校验）")
        parts.append("弹窗→行内红字（inline validation）")
    elif "权限" in major:
        parts.append("页面加载时前置判断权限，入口屏蔽+兜底弹窗")
    elif "系统异常" in major:
        parts.append("统一请求拦截层包装技术裸错误")
        parts.append("弹窗→Toast/占位（页面级=占位+重试，操作级=Toast+重试）")
    elif "状态" in major:
        parts.append("页面加载时获取状态，按钮置灰+banner 替代操作后弹窗")
    if experience.copy_severity.value != "轻微":
        parts.append("文案优化（去技术术语/去责备语气/补充操作指引）")
    return "；".join(parts) if parts else "待细化"


def _build_verification_plan(features) -> str:
    """构建回检方案"""
    major = features.major_category
    if "校验" in major:
        return "回检指标：任务一次性完成率、报错压降率。回检周期：上线后7天首次，30天二次。"
    elif "权限" in major:
        return "回检指标：报错压降率、引导点击率。回检周期：上线后7天首次。"
    elif "系统异常" in major:
        return "回检指标：报错压降率、满意度得分。回检周期：上线后30天。"
    return "回检指标：报错压降率。回检周期：上线后30天。若缺乏埋点条件，需补充埋点方案。"
