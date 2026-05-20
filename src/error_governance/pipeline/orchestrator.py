"""Pipeline 主编排器 — SKILL-01 11 步实现"""

import os
import uuid
from datetime import datetime
from typing import Optional, Callable

from error_governance.models.error_item import ErrorItem, ErrorFeatures
from error_governance.models.diagnosis_result import DiagnosisResult
from error_governance.models.human_review import HumanReviewCard, HumanReviewResponse
from error_governance.models.workflow_state import (
    WorkflowState, RunLog, RunStatus, ErrorItemStatus,
)
from error_governance.models.evidence import EvidenceSummary
from error_governance.config import LOW_CONFIDENCE_THRESHOLD

from error_governance.pipeline.input_validator import validate_item
from error_governance.pipeline.feature_extractor import extract
from error_governance.pipeline.evidence_retriever import retrieve, get_available, get_unavailable
from error_governance.pipeline.evidence_relevance import assess as assess_evidence
from error_governance.pipeline.experience_evaluator import evaluate as evaluate_experience
from error_governance.pipeline.priority_scorer import assess_priority, estimate_effect
from error_governance.pipeline.path_decider import decide
from error_governance.pipeline.report_generator import generate as generate_report
from error_governance.pipeline.review_card_generator import generate as generate_review_card

from error_governance.state.ledger_writer import write_diagnosis, write_evidence, update_review
from error_governance.state.run_store import save_run_item, add_governance_id
from error_governance.human_gate.question_builder import save_question_file
from error_governance.config import ARTIFACTS_RUN_LOGS


class PipelineResult:
    def __init__(self):
        self.success = False
        self.needs_human = False
        self.governance_id = ""
        self.run_id = ""
        self.diagnosis: Optional[DiagnosisResult] = None
        self.review_card: Optional[HumanReviewCard] = None
        self.state: Optional[WorkflowState] = None
        self.report_path = ""
        self.review_card_path = ""
        self.question_path = ""
        self.run_log_path = ""
        self.blocked_at = ""
        self.block_reason = ""


class PipelineOrchestrator:
    """SKILL-01 11 步编排"""

    def run(self, error_item: ErrorItem,
            human_callback: Optional[Callable[[DiagnosisResult, HumanReviewCard], HumanReviewResponse]] = None,
            run_id: str = "",
            ) -> PipelineResult:
        result = PipelineResult()
        gid = f"GOV_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        result.governance_id = gid
        result.run_id = run_id

        run_log = RunLog(run_id=gid, error_id=error_item.error_code or gid)
        run_log.current_status = ErrorItemStatus.DIAGNOSING.value

        # Step 01
        ok, msg = validate_item(error_item)
        if not ok:
            result.blocked_at = "01"; result.block_reason = msg
            return result
        run_log.step_01_input_ok = True

        # Step 02
        features = extract(error_item)
        run_log.step_02_feature_ok = True
        run_log.step_03_keyword_gen_ok = True

        # Step 03-04
        evidence = retrieve(error_item, features)
        run_log.step_04_evidence_search_ok = True
        run_log.evidence_sources_available = get_available()
        run_log.evidence_sources_unavailable = get_unavailable()

        # Step 05
        relevance_msg, needs_human = assess_evidence(evidence)
        if needs_human and evidence.total_evidence_count == 0:
            run_log.exception_type = "无证据"
        run_log.step_05_evidence_relevance_ok = True

        # Step 06
        experience = evaluate_experience(error_item, features)
        run_log.step_06_experience_ok = True

        # Step 07
        priority = assess_priority(error_item, features, evidence, experience)
        run_log.step_07_priority_ok = True

        # Step 08
        effect = estimate_effect(error_item, features, evidence, priority)
        run_log.step_08_effect_ok = True

        # Step 09
        path, path_rationale = decide(features, experience)
        run_log.step_09_path_ok = True

        # 置信度
        conf_score = 0.5
        if evidence.sufficiency.sufficient_for_diagnosis: conf_score += 0.2
        if evidence.sufficiency.sufficient_for_priority_scoring: conf_score += 0.2
        if evidence.sufficiency.sufficient_for_effect_estimation: conf_score += 0.1

        # 优化方向与回检方案
        optimization = _build_optimization(features, experience)
        verification = _build_verification(features)

        diagnosis = DiagnosisResult(
            governance_id=gid, error_input=error_item, features=features,
            evidence=evidence, experience=experience, priority=priority,
            effect=effect, recommended_path=path, path_rationale=path_rationale,
            optimization_direction=optimization, verification_plan=verification,
            confidence_score=conf_score,
        )

        effective_run_id = run_id if run_id else gid

        # Step 10
        report_path = generate_report(diagnosis, effective_run_id)
        result.report_path = report_path
        run_log.step_10_report_ok = True

        # Step 11
        review_card = HumanReviewCard(
            governance_id=gid, error_message=error_item.error_message,
            ai_summary=f"{features.major_category}/{features.minor_category} — {priority.priority.value}({priority.total_score}分)",
            recommended_path=path.value, priority=priority.priority.value,
            evidence_summary_text=f"共{evidence.total_evidence_count}条，强相关{evidence.strong_relevance_count}条",
            review_items=["证据相关性", "AI诊断准确性", "路径建议合理性", "优先级合理性"],
        )
        review_card_path = generate_review_card(diagnosis, effective_run_id)
        result.review_card_path = review_card_path
        run_log.step_11_review_card_ok = True

        # 写入 run_log
        run_log_path = _write_run_log(run_log, diagnosis, effective_run_id)
        result.run_log_path = run_log_path

        # 写入台账和证据
        write_diagnosis(diagnosis)
        write_evidence(diagnosis)

        # 保存运行状态
        wf_state = WorkflowState(
            governance_id=gid,
            run_status=RunStatus.WAITING_FOR_HUMAN,
            item_status=ErrorItemStatus.WAITING_HUMAN,
            run_log=run_log,
        )
        if run_id:
            save_run_item(run_id, gid, wf_state)
            add_governance_id(run_id, gid)

        # 生成人工复核问题卡
        question_path = save_question_file(diagnosis, review_card, effective_run_id)
        result.question_path = question_path

        result.success = True
        result.diagnosis = diagnosis
        result.review_card = review_card
        result.state = wf_state
        result.needs_human = True

        if human_callback:
            resp = human_callback(diagnosis, review_card)
            # 人工结论回写
            update_review(gid, resp.human_review_result, resp.reviewer, resp.human_review_comment or "")
            result.needs_human = False

        return result


def _write_run_log(run_log, diagnosis, run_id: str = "") -> str:
    """生成单条 error_id 的运行日志 → artifacts/run_logs/{run_id}/{gid}_run_log.md"""
    run_dir = os.path.join(ARTIFACTS_RUN_LOGS, run_id) if run_id else ARTIFACTS_RUN_LOGS
    os.makedirs(run_dir, exist_ok=True)
    gid = diagnosis.governance_id
    path = os.path.join(run_dir, f"{gid}_run_log.md")

    steps = [
        ("01 输入标准化", run_log.step_01_input_ok),
        ("02 特征提取", run_log.step_02_feature_ok),
        ("03 关键词生成", run_log.step_03_keyword_gen_ok),
        ("04 证据检索", run_log.step_04_evidence_search_ok),
        ("05 证据相关性", run_log.step_05_evidence_relevance_ok),
        ("06 体验评估", run_log.step_06_experience_ok),
        ("07 优先级评分", run_log.step_07_priority_ok),
        ("08 成效预估", run_log.step_08_effect_ok),
        ("09 路径判定", run_log.step_09_path_ok),
        ("10 报告生成", run_log.step_10_report_ok),
        ("11 复核卡", run_log.step_11_review_card_ok),
    ]
    steps_md = "\n".join(f"| {name} | {'✅' if ok else '❌'} |" for name, ok in steps)

    md = f"""# Run Log — {gid}

**Run ID**: {run_id}
**时间**: {run_log.timestamp}
**状态**: {run_log.current_status}

## 步骤执行

| 步骤 | 状态 |
|------|------|
{steps_md}

## 数据源
- 可用: {', '.join(run_log.evidence_sources_available) if run_log.evidence_sources_available else '无'}
- 不可用: {', '.join(run_log.evidence_sources_unavailable) if run_log.evidence_sources_unavailable else '无'}

## 诊断摘要
- 分类: {diagnosis.features.major_category} / {diagnosis.features.minor_category}
- 优先级: {diagnosis.priority.priority.value}（{diagnosis.priority.total_score} 分）
- 路径: {diagnosis.recommended_path.value}
- 置信度: {diagnosis.confidence_score:.2%}

## 异常
{run_log.exception_type or '无'}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def _build_optimization(features, experience) -> str:
    parts = []
    m = features.major_category
    if "校验" in m:
        parts += ["校验时机前置（输入失焦/提交前校验）", "弹窗→行内红字（inline validation）"]
    elif "权限" in m:
        parts.append("页面加载时前置判断权限，入口屏蔽+兜底弹窗")
    elif "系统异常" in m:
        parts += ["统一请求拦截层包装技术裸错误", "弹窗→Toast/占位"]
    elif "状态" in m:
        parts.append("页面加载时获取状态，按钮置灰+banner 替代操作后弹窗")
    if experience.copy_severity.value != "轻微":
        parts.append("文案优化（去技术术语/去责备语气/补充操作指引）")
    return "；".join(parts) if parts else "待细化"


def _build_verification(features) -> str:
    m = features.major_category
    if "校验" in m: return "回检指标：任务一次性完成率、报错压降率。周期：7天首次，30天二次。"
    if "权限" in m: return "回检指标：报错压降率、引导点击率。周期：7天首次。"
    if "系统异常" in m: return "回检指标：报错压降率、满意度。周期：30天。"
    return "回检指标：报错压降率。周期：30天。若缺埋点条件，需补充埋点方案。"
