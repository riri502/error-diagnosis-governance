"""Step 01: 输入标准化与校验

- 字段校验: 参考 rules/DOC-00
- 关键字段缺失 → 阻断，写入待补充信息池
- 降级字段缺失 → 警告，继续运行
- error_id 重复 → 标记，继续但警告
- 不修改原始输入文件
"""

from dataclasses import dataclass, field
from datetime import datetime
from error_governance.models.error_item import ErrorItem
from error_governance.adapters.file_input_adapter import ReadResult


@dataclass
class ValidationResult:
    """校验结果"""
    valid: bool = True
    errors: list[ErrorItem] = field(default_factory=list)
    blocked_items: list[dict] = field(default_factory=list)    # 被阻断的条目
    warnings: list[dict] = field(default_factory=list)          # 降级警告
    duplicate_ids: list[str] = field(default_factory=list)      # 重复 error_id
    field_report: dict = field(default_factory=dict)            # 字段报告
    total_input: int = 0
    valid_count: int = 0
    blocked_count: int = 0
    written_to_pool: bool = False                               # 是否已写入待补充信息池


def validate(read_result: ReadResult) -> ValidationResult:
    """校验 ReadResult 中的报错条目

    校验内容:
      1. 关键字段完整性（已在 file_input_adapter 中处理，此处在 blocked_rows 增补说明）
      2. error_id 唯一性
      3. error_message 语义有效性（非纯空白、非占位符）
    """
    v = ValidationResult()
    v.field_report = read_result.field_report
    v.total_input = read_result.total_rows
    v.warnings = list(read_result.warnings)
    v.duplicate_ids = list(read_result.duplicate_ids)

    # 透传被阻断的行
    for blocked in read_result.blocked_rows:
        v.blocked_items.append({
            "row_index": blocked.get("row_index"),
            "error_id": blocked.get("error_id", ""),
            "block_reason": blocked.get("reason", ""),
            "timestamp": datetime.now().isoformat(),
        })

    # 透传已解析成功的 errors
    v.errors = list(read_result.errors)

    # error_id 唯一性检查（重复条目标记警告）
    seen_ids = {}
    for item in v.errors:
        eid = item.error_code or ""
        if eid and eid in seen_ids:
            v.warnings.append({
                "error_id": eid,
                "field": "error_code",
                "warning": f"error_code '{eid}' 重复出现（首次在第 {seen_ids[eid]+1} 行），非阻断但建议检查",
            })
        elif eid:
            seen_ids[eid] = len(v.errors)

    # error_message 语义检查
    for item in v.errors:
        msg = item.error_message.strip()
        if len(msg) < 2:
            v.blocked_items.append({
                "error_id": item.error_code or "(无)",
                "block_reason": "error_message 过短（不足 2 字符），疑似无效数据",
                "timestamp": datetime.now().isoformat(),
            })
        elif msg in ("N/A", "null", "None", "(空)", "无"):
            v.warnings.append({
                "error_id": item.error_code or "(无)",
                "field": "error_message",
                "warning": f"error_message 为占位符 '{msg}'，可能为无效数据",
            })

    v.valid_count = len(v.errors)
    v.blocked_count = len(v.blocked_items)
    v.valid = v.blocked_count == 0

    return v


def format_validation_report(v: ValidationResult) -> str:
    """生成可读的校验报告"""
    lines = [
        "=" * 50,
        "  输入校验报告",
        "=" * 50,
        f"  总行数: {v.total_input}",
        f"  有效条目: {v.valid_count}",
        f"  阻断条目: {v.blocked_count}",
        f"  重复 error_id: {len(v.duplicate_ids)}",
        f"  警告数: {len(v.warnings)}",
        f"  校验通过: {'✅ 是' if v.valid else '❌ 否（存在阻断条目）'}",
    ]

    # 字段报告
    if v.field_report:
        lines.append("\n[字段报告]")
        for field, status in v.field_report.items():
            icon = "✅" if status == "found" else "⚠️"
            lines.append(f"  {icon} {field}: {status}")

    # 阻断条目
    if v.blocked_items:
        lines.append(f"\n[阻断条目] ({len(v.blocked_items)} 条)")
        for item in v.blocked_items[:10]:  # 最多展示 10 条
            lines.append(f"  ❌ {item.get('error_id', '?')} | {item.get('block_reason', '')}")
        if len(v.blocked_items) > 10:
            lines.append(f"  ... 共 {len(v.blocked_items)} 条")

    # 警告
    if v.warnings:
        lines.append(f"\n[警告] ({len(v.warnings)} 条)")
        for w in v.warnings[:10]:
            lines.append(f"  ⚠️ {w.get('error_id', '?')} | {w.get('field', '')}: {w.get('warning', '')}")
        if len(v.warnings) > 10:
            lines.append(f"  ... 共 {len(v.warnings)} 条")

    # 重复
    if v.duplicate_ids:
        lines.append(f"\n[重复 error_code]")
        for eid in v.duplicate_ids:
            lines.append(f"  🔄 {eid}")

    lines.append("=" * 50)
    return "\n".join(lines)


# ── 向后兼容 ──

def validate_item(error_item: ErrorItem) -> tuple[bool, str]:
    """校验单条 ErrorItem（向后兼容旧接口）"""
    if not error_item.error_message:
        return False, "报错提示为空，无法继续"
    return True, ""
