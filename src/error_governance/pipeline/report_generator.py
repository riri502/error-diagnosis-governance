"""Step 10: 综合诊断报告生成 → artifacts/diagnosis_reports/{run_id}/{error_id}_diagnosis_report.md"""

import os
from datetime import datetime
from error_governance.models.diagnosis_result import DiagnosisResult
from error_governance.config import ARTIFACTS_DIAGNOSIS


def generate(diagnosis: DiagnosisResult, run_id: str) -> str:
    run_dir = os.path.join(ARTIFACTS_DIAGNOSIS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    gid = diagnosis.governance_id
    path = os.path.join(run_dir, f"{gid}_diagnosis_report.md")

    d = diagnosis
    inp = d.error_input
    fea = d.features
    evi = d.evidence
    exp = d.experience
    pri = d.priority
    eff = d.effect

    sources = set(i.source_type.value for i in evi.items)
    sources_str = ', '.join(sources) if sources else '无可用数据源'
    unavailable = ', '.join(evi.unavailable_sources) if evi.unavailable_sources else '无'

    lines = []
    for item in evi.items:
        lines.append(f"- [{item.relevance_level.value}] [{item.source_type.value}] {item.evidence_summary} (可信度: {item.confidence.value})")

    md = f"""# 报错诊断报告

**治理条目 ID**: {gid} | **Run**: {run_id} | **生成时间**: {datetime.now().isoformat()}

---

## 体验问题描述
- **报错文案**: {inp.error_message}
- **错误码**: {inp.error_code or '无'} | **URL**: {inp.url or '无'} | **路由**: {inp.page_route or '无'}
- **触发场景**: {inp.trigger_scenario or '无'} | **报错次数**: {inp.error_count}

### 特征分类
- 大类: {fea.major_category} | 小类: {fea.minor_category}
- 任务类型: {fea.task_type} | 校验逻辑: {fea.validation_logic}
- 报错原因: {fea.error_reason} | 模块: {fea.business_module}

---

## 多源证据摘要
- 已检索数据源: {sources_str}
- 不可用数据源: {unavailable}
- 强相关: {evi.strong_relevance_count} | 中相关: {evi.medium_relevance_count} | 弱相关: {evi.weak_relevance_count}
- 证据冲突: {'是' if evi.conflict.has_conflict else '否'}
- 充分性: 诊断{'充足' if evi.sufficiency.sufficient_for_diagnosis else '不足'} / 评分{'充足' if evi.sufficiency.sufficient_for_priority_scoring else '不足'}

### 关键证据清单
{chr(10).join(lines) if lines else '无可用证据'}

---

## 体验标准评估
- 时机: {exp.timing_issue or '无显著问题'} ({exp.timing_severity.value})
- 形式: {exp.form_issue or '无显著问题'} ({exp.form_severity.value})
- 文案: {exp.copy_issue or '无显著问题'} ({exp.copy_severity.value})
- 交互: {exp.interaction_issue or '无显著问题'} ({exp.interaction_severity.value})

---

## 优先级评估
- **综合**: {pri.priority.value}（{pri.total_score} 分）
- 旅程 {pri.journey_impact_score} | 体验 {pri.experience_violation_score} | 客户 {pri.customer_impact_score} | 规模 {pri.error_scale_score} | 可行 {pri.fix_feasibility_score}

## 预计成效
- 主指标: {eff.primary_metric} | 预估: {eff.estimated_change} | 可信度: {eff.confidence.value}
- 依据: {'; '.join(eff.basis)}
- 限制: {'; '.join(eff.limitations) if eff.limitations else '无'}

## 实施路径
- 建议: {d.recommended_path.value} | 理由: {d.path_rationale}

## 优化方向
{d.optimization_direction or '待细化'}

## 回检方案
{d.verification_plan or '待细化'}

## 置信度
{d.confidence_score:.2%}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path
