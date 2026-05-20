"""Step 06: 体验问题评估 — DOC-02 四维度"""

import re
from error_governance.models.diagnosis_result import ExperienceAssessment, ExperienceSeverity


def evaluate(error_item, features) -> ExperienceAssessment:
    text = error_item.error_message

    # 时机
    timing_issue, timing_sev = _evaluate_timing(features)
    # 形式
    form_issue, form_sev = _evaluate_form(text)
    # 文案
    copy_issue, copy_sev = _evaluate_copy(text)
    # 交互
    interaction_issue, interaction_sev = _evaluate_interaction(text)

    return ExperienceAssessment(
        timing_issue=timing_issue, timing_severity=timing_sev,
        form_issue=form_issue, form_severity=form_sev,
        copy_issue=copy_issue, copy_severity=copy_sev,
        interaction_issue=interaction_issue, interaction_severity=interaction_sev,
    )


def _evaluate_timing(features):
    major, minor = features.major_category, features.minor_category
    if "校验" in major:
        return "数据校验类理想时机应为前端失焦/提交前校验", ExperienceSeverity.MODERATE
    if "权限" in major:
        return "权限类理想时机应为页面加载时前置判断（入口屏蔽）", ExperienceSeverity.MODERATE
    if minor in ["已锁定/已冻结/已结账", "流程中/处理中"]:
        return "状态类可在页面加载时判断并渲染 banner/置灰，不应每次弹窗", ExperienceSeverity.MODERATE
    return "时机接近最佳或无法前置", ExperienceSeverity.MINOR


def _evaluate_form(text):
    if re.search(r'Network Error|timeout|ECONNABORTED|[45]\d{2}\s', text, re.IGNORECASE):
        return "技术裸错误透传（英文/HTTP码），应包装为用户中文提示", ExperienceSeverity.CRITICAL
    if "！" in text or "!" in text:
        return "使用感叹号，语气较重", ExperienceSeverity.MODERATE
    return "形式暂无显著问题", ExperienceSeverity.MINOR


def _evaluate_copy(text):
    issues = []
    if re.search(r'接口|远程服务|token|签名|参数.*不能为空', text):
        issues.append("技术术语暴露")
    if re.search(r'[A-Z_]{3,}', text):
        issues.append("字段名可能为数据库字段名")
    if re.search(r'请检查|请刷新', text):
        issues.append("模糊引导（'请检查''请刷新'）")
    if re.search(r'请勿|不能！|不允许！', text):
        issues.append("责备语气")
    has_what = bool(re.search(r'[错误异常失败]|[不无]存在|[不无]能|[不无]允许', text))
    has_how = bool(re.search(r'请联系|请前往|请检查|请重新|请修改|请选择', text))
    if has_what and not has_how:
        issues.append("信息缺失：有报错无操作指引")

    if len(issues) >= 2:
        return "；".join(issues), ExperienceSeverity.CRITICAL
    elif len(issues) == 1:
        return issues[0], ExperienceSeverity.MODERATE
    return "文案暂无显著问题", ExperienceSeverity.MINOR


def _evaluate_interaction(text):
    if not re.search(r'请联系|请前往|请检查|请重新|返回|重试|知道了', text):
        return "报错后缺少明确的操作出口", ExperienceSeverity.MODERATE
    return "有基本操作出口", ExperienceSeverity.MINOR
