"""DOC-02 体验问题评估 — 基于规则的四维度评估（时机/形式/文案/交互）"""

import re
from error_diagnosis.models import (
    ErrorInput, ErrorFeatures, ExperienceAssessment, ExperienceSeverity,
)


def evaluate_experience(input: ErrorInput, features: ErrorFeatures) -> ExperienceAssessment:
    """按 DOC-02 对报错进行四维度体验评估"""

    text = input.error_message

    # ── 现场评估 ──
    timing_issue, timing_sev = _evaluate_timing(features)

    # ── 形式评估 ──
    form_issue, form_sev = _evaluate_form(text)

    # ── 文案评估 ──
    copy_issue, copy_sev = _evaluate_copy(text)

    # ── 交互评估 ──
    interaction_issue, interaction_sev = _evaluate_interaction(text)

    return ExperienceAssessment(
        timing_issue=timing_issue, timing_severity=timing_sev,
        form_issue=form_issue, form_severity=form_sev,
        copy_issue=copy_issue, copy_severity=copy_sev,
        interaction_issue=interaction_issue, interaction_severity=interaction_sev,
    )


def _evaluate_timing(features: ErrorFeatures) -> tuple[str, ExperienceSeverity]:
    """评估报错时机（简化版——MVP 基于分类推断）"""
    # 基于报错类型推断时机是否合理
    minor = features.minor_category
    # 数据校验类理论上应在前端/失焦时拦截，若走到"后端弹窗"则时机滞后
    if "校验" in features.major_category:
        return "数据校验类报错理想时机应为前端失焦/提交前校验，当前可能为提交后弹窗", ExperienceSeverity.MODERATE
    # 权限类应在页面加载/路由进入时前置判断
    if "权限" in features.major_category:
        return "权限类报错理想时机应为页面加载时前置判断（入口屏蔽），当前可能为操作触发后弹窗", ExperienceSeverity.MODERATE
    # 业务状态类部分可前置
    if minor in ["已锁定/已冻结/已结账", "流程中/处理中"]:
        return "该状态类报错可在页面加载时判断并渲染 banner/按钮置灰，不应每次操作才弹窗", ExperienceSeverity.MODERATE
    return "当前时机接近最佳或无法前置", ExperienceSeverity.MINOR


def _evaluate_form(text: str) -> tuple[str, ExperienceSeverity]:
    """评估形式（简化版——MVP 基于文案特征推断）"""
    # 检查是否为技术裸错误（英文/HTPP码透传）
    if re.search(r'Network Error|timeout|ECONNABORTED|[45]\d{2}\s', text, re.IGNORECASE):
        return "技术裸错误透传给用户（英文/HTTP码），应包装为用户可理解的中文提示", ExperienceSeverity.CRITICAL
    # 检查是否使用感叹号（弹窗阻断的典型特征）
    if "！" in text or "!" in text:
        return "使用感叹号，语气较重，可能为弹窗阻断形式", ExperienceSeverity.MODERATE
    return "当前形式暂无显著问题", ExperienceSeverity.MINOR


def _evaluate_copy(text: str) -> tuple[str, ExperienceSeverity]:
    """评估文案（简化版——MVP 基于 DOC-02 4.5 现状问题清单）"""
    issues = []

    # 技术术语暴露
    if re.search(r'接口|远程服务|token|签名|参数.*不能为空', text):
        issues.append("技术术语暴露（接口/远程/token/签名/参数）")
    # 字段名不可读
    if re.search(r'[A-Z_]{3,}', text):
        issues.append("字段名可能为数据库字段名而非用户可读 label")
    # 模糊引导
    if re.search(r'请检查|请刷新', text):
        issues.append("模糊引导（'请检查''请刷新'），未给出具体操作")
    # 责备语气
    if re.search(r'请勿|不能！|不允许！', text):
        issues.append("责备语气（'请勿''不能''不允许'）")
    # 信息缺失（有 what 无 how）
    has_what = bool(re.search(r'[错误异常失败]|[不无]存在|[不无]能|[不无]允许', text))
    has_how = bool(re.search(r'请联系|请前往|请检查|请重新|请修改|请选择', text))
    if has_what and not has_how:
        issues.append("信息缺失：告知了错误但未给出解决方案或操作指引")

    if len(issues) >= 2:
        return "；".join(issues), ExperienceSeverity.CRITICAL
    elif len(issues) == 1:
        return issues[0], ExperienceSeverity.MODERATE
    return "文案暂无显著问题", ExperienceSeverity.MINOR


def _evaluate_interaction(text: str) -> tuple[str, ExperienceSeverity]:
    """评估交互（简化版——MVP 基于文案推断出口情况）"""
    # 检查是否有操作出口
    has_exit = bool(re.search(r'请联系|请前往|请检查|请重新|返回|重试|知道了', text))
    if not has_exit:
        return "报错后缺少明确的操作出口，用户可能被困住", ExperienceSeverity.MODERATE
    return "有基本操作出口", ExperienceSeverity.MINOR
