"""解析人工复核反馈文件 — {run_id}_user_response.md

期望格式：以 `### error_id: GOV_xxx` 开头，每个字段独占一行：
  human_review_result: <枚举值>
  evidence_review_result: <枚举值>
  is_reproducible: <是/否/不确定>
  is_optimization_needed: <是/否/待讨论>
  human_review_comment: <任意文本>
  path_adjustment: <任意文本>
  priority_adjustment: <任意文本>
  next_action: <任意文本>
"""

import os
import re
from error_governance.models.human_review import (
    HumanReviewResponse, ParseError, ParseResult,
    HUMAN_REVIEW_RESULTS, EVIDENCE_REVIEW_RESULTS,
)

REPRODUCIBLE_VALUES = {"是", "否", "不确定"}
OPTIMIZATION_VALUES = {"是", "否", "待讨论"}


def parse_file(filepath: str) -> ParseResult:
    """解析用户反馈 Markdown 文件

    Returns:
        ParseResult: 包含成功解析的 responses 和失败的 errors
    """
    result = ParseResult()

    if not os.path.exists(filepath):
        result.success = False
        result.errors.append(ParseError(
            message=f"文件不存在: {filepath}",
        ))
        return result

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    sections = re.split(r'(?=### error_id:)', content)

    for section in sections:
        id_match = re.match(r'### error_id:\s*(\S+)', section)
        if not id_match:
            continue

        error_id = id_match.group(1).strip()
        parsed = _parse_section(error_id, section)
        if isinstance(parsed, ParseError):
            result.errors.append(parsed)
        else:
            result.responses.append(parsed)

    result.total_items = len(result.responses) + len(result.errors)
    result.parsed_items = len(result.responses)
    result.success = len(result.errors) == 0 and len(result.responses) > 0

    return result


def _parse_section(error_id: str, section: str):
    """解析单个条目区块"""

    def _extract(field: str) -> str:
        pattern = rf'{field}\s*[:：]\s*(.*?)(?=\n\s*\n|\n\s*[a-z_]+[:：]|\Z)'
        match = re.search(pattern, section, re.DOTALL)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'\s*\(示例.*?\)\s*$', '', val)
            return val
        return ""

    human_review = _extract("human_review_result")
    evidence_review = _extract("evidence_review_result")
    is_reproducible = _extract("is_reproducible")
    is_optimization = _extract("is_optimization_needed")

    # ── 校验 ──
    if not human_review:
        return ParseError(
            error_id=error_id, field="human_review_result",
            message=f"human_review_result 为空，必须填写以下之一: {', '.join(HUMAN_REVIEW_RESULTS)}",
            line_content=section[:200],
        )

    if human_review not in HUMAN_REVIEW_RESULTS:
        return ParseError(
            error_id=error_id, field="human_review_result",
            message=f"无效值 '{human_review}'，必须为: {', '.join(HUMAN_REVIEW_RESULTS)}",
            line_content=section[:200],
        )

    if not evidence_review:
        return ParseError(
            error_id=error_id, field="evidence_review_result",
            message=f"evidence_review_result 为空，必须填写: {', '.join(EVIDENCE_REVIEW_RESULTS)}",
            line_content=section[:200],
        )

    if evidence_review not in EVIDENCE_REVIEW_RESULTS:
        return ParseError(
            error_id=error_id, field="evidence_review_result",
            message=f"无效值 '{evidence_review}'，必须为: {', '.join(EVIDENCE_REVIEW_RESULTS)}",
            line_content=section[:200],
        )

    if not is_reproducible:
        return ParseError(
            error_id=error_id, field="is_reproducible",
            message="is_reproducible 为空，必须填写: 是 / 否 / 不确定",
            line_content=section[:200],
        )

    if is_reproducible not in REPRODUCIBLE_VALUES:
        return ParseError(
            error_id=error_id, field="is_reproducible",
            message=f"无效值 '{is_reproducible}'，必须为: 是 / 否 / 不确定",
            line_content=section[:200],
        )

    if not is_optimization:
        return ParseError(
            error_id=error_id, field="is_optimization_needed",
            message="is_optimization_needed 为空，必须填写: 是 / 否 / 待讨论",
            line_content=section[:200],
        )

    if is_optimization not in OPTIMIZATION_VALUES:
        return ParseError(
            error_id=error_id, field="is_optimization_needed",
            message=f"无效值 '{is_optimization}'，必须为: 是 / 否 / 待讨论",
            line_content=section[:200],
        )

    # 复核人
    reviewer_match = re.search(r'复核人\s*[:：]\s*(.+)', section)
    reviewer = reviewer_match.group(1).strip() if reviewer_match else ""

    return HumanReviewResponse(
        error_id=error_id,
        human_review_result=human_review,
        evidence_review_result=evidence_review,
        is_reproducible=is_reproducible,
        is_optimization_needed=is_optimization,
        human_review_comment=_extract("human_review_comment"),
        path_adjustment=_extract("path_adjustment"),
        priority_adjustment=_extract("priority_adjustment"),
        next_action=_extract("next_action"),
        reviewer=reviewer,
    )


def format_parse_errors(result: ParseResult) -> str:
    """格式化解析错误为可读提示"""
    if result.success:
        return ""

    lines = ["\n❌ 解析失败，以下条目存在错误：\n"]
    for err in result.errors:
        lines.append("---")
        lines.append(f"error_id: {err.error_id}")
        lines.append(f"字段: {err.field}")
        lines.append(f"错误: {err.message}")
        if err.line_content:
            lines.append(f"原文片段: {err.line_content[:100]}...")
    lines.append(f"\n共 {len(result.errors)} 条错误，请修正后重新执行。")
    lines.append("反馈文件格式参见 questions.md 中的「用户反馈模板」")
    return "\n".join(lines)
