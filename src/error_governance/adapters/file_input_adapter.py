"""本地文件输入适配器 — 读取 CSV，校验字段，标准化输出

字段规则参考: rules/DOC-00_数据源盘点与输入输出契约.md
"""

import csv
import os
import hashlib
from datetime import datetime
from dataclasses import dataclass, field
from error_governance.adapters.base_adapter import BaseInputAdapter
from error_governance.models.error_item import ErrorItem
from error_governance.config import (
    INPUT_FIELD_ALIASES, DATA_INBOX, DATA_PROCESSED,
)

# ── DOC-00 字段定义 ──

# 关键字段（缺失则阻断该条记录）
CRITICAL_FIELDS = ["error_message"]

# 降级字段（缺失可降级继续，写入 warning）
DEGRADABLE_FIELDS = {
    "error_code": {"default": "", "warning": "缺少错误码，降级为空"},
    "trigger_scenario": {"default": "", "warning": "缺少触发场景，降级为空"},
}

# 可选字段（缺失无影响）
OPTIONAL_FIELDS = ["url", "page_route"]

# 数值字段（需转为 int，转换失败降级为默认值）
NUMERIC_FIELDS = {
    "error_count": 1,
}

# 所有标准字段
ALL_STANDARD_FIELDS = ["error_code", "error_message", "url", "page_route", "trigger_scenario", "error_count"]


@dataclass
class ReadResult:
    """读取结果"""
    success: bool = True
    errors: list[ErrorItem] = field(default_factory=list)
    blocked_rows: list[dict] = field(default_factory=list)   # 被阻断的行
    warnings: list[dict] = field(default_factory=list)       # 降级警告 [{row_index, error_id, field, warning}]
    field_report: dict = field(default_factory=dict)         # {field: found/missing/degraded}
    total_rows: int = 0
    valid_rows: int = 0
    blocked_rows_count: int = 0
    duplicate_ids: list[str] = field(default_factory=list)
    error_message: str = ""                                  # 文件级错误


class FileInputAdapter(BaseInputAdapter):
    """从 CSV 文件读取报错数据

    处理流程:
      1. 读取 CSV → 自动识别字段别名
      2. 逐行校验字段 → 关键字段缺失则阻断
      3. 降级字段缺失 → 写入 warning，继续
      4. error_id 唯一性检查
      5. 输出标准化 CSV 到 data/processed/
      6. 返回 ReadResult（含 errors + blocked_rows + warnings）
    """

    def __init__(self, default_path: str = None):
        self.default_path = default_path or os.path.join(DATA_INBOX, "errors.csv")

    # ── 主入口 ──

    def read_errors(self, filepath: str = "") -> list[ErrorItem]:
        """便捷方法 — 只返回成功解析的 ErrorItem 列表（向后兼容）"""
        result = self.read(filepath or self.default_path)
        return result.errors

    def read(self, filepath: str = "") -> ReadResult:
        """完整读取 — 返回 ReadResult"""
        path = filepath or self.default_path
        result = ReadResult()

        # 文件检查
        if not os.path.exists(path):
            result.success = False
            result.error_message = f"文件不存在: {path}"
            return result

        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                raw_fieldnames = list(reader.fieldnames or [])
                result.total_rows = 0
                result.valid_rows = 0

                # 建立字段映射
                header_map, field_report = self._build_header_map(raw_fieldnames)
                result.field_report = field_report

                # 逐行处理
                for row_idx, row in enumerate(reader):
                    result.total_rows += 1
                    mapped, row_warnings = self._map_row(row, header_map)

                    # 关键字段检查
                    blocked = False
                    for crit in CRITICAL_FIELDS:
                        if not mapped.get(crit):
                            result.blocked_rows.append({
                                "row_index": row_idx + 1,  # 1-indexed
                                "error_id": mapped.get("error_code", f"ROW_{row_idx+1}"),
                                "field": crit,
                                "reason": f"关键字段 '{crit}' 缺失或为空，阻断该条记录",
                                "raw_row": dict(row),
                            })
                            result.blocked_rows_count += 1
                            blocked = True
                            break

                    if blocked:
                        continue

                    # 降级警告收集
                    for w in row_warnings:
                        result.warnings.append({
                            "row_index": row_idx + 1,
                            "error_id": mapped.get("error_code", f"ROW_{row_idx+1}"),
                            "field": w["field"],
                            "warning": w["warning"],
                        })

                    # 构建 ErrorItem
                    try:
                        item = ErrorItem(
                            error_code=mapped.get("error_code", ""),
                            error_message=mapped["error_message"],
                            url=mapped.get("url", ""),
                            page_route=mapped.get("page_route", ""),
                            trigger_scenario=mapped.get("trigger_scenario", ""),
                            error_count=int(mapped.get("error_count", "1") or "1"),
                        )
                        result.errors.append(item)
                        result.valid_rows += 1
                    except ValueError as e:
                        result.blocked_rows.append({
                            "row_index": row_idx + 1,
                            "error_id": mapped.get("error_code", f"ROW_{row_idx+1}"),
                            "reason": f"数据转换失败: {e}",
                        })
                        result.blocked_rows_count += 1

                # error_id 唯一性检查
                result = self._check_uniqueness(result)

        except UnicodeDecodeError as e:
            result.success = False
            result.error_message = f"文件编码错误（期望 UTF-8）: {e}"
        except csv.Error as e:
            result.success = False
            result.error_message = f"CSV 解析错误: {e}"
        except PermissionError:
            result.success = False
            result.error_message = f"无权限读取文件: {path}"
        except Exception as e:
            result.success = False
            result.error_message = f"读取文件时发生未知错误: {type(e).__name__}: {e}"

        return result

    # ── 标准化输出 ──

    def write_standardized(self, result: ReadResult, run_id: str) -> str:
        """将标准化后的数据输出到 data/processed/{run_id}_standardized_errors.csv"""
        os.makedirs(DATA_PROCESSED, exist_ok=True)
        path = os.path.join(DATA_PROCESSED, f"{run_id}_standardized_errors.csv")

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=ALL_STANDARD_FIELDS)
            writer.writeheader()
            for item in result.errors:
                writer.writerow({
                    "error_code": item.error_code,
                    "error_message": item.error_message,
                    "url": item.url or "",
                    "page_route": item.page_route or "",
                    "trigger_scenario": item.trigger_scenario or "",
                    "error_count": item.error_count,
                })
        return path

    # ── 内部方法 ──

    def _build_header_map(self, fieldnames: list[str]) -> tuple[dict, dict]:
        """建立列名→标准字段名的映射，同时生成字段报告"""
        header_map = {}
        field_report = {}

        for std_name in ALL_STANDARD_FIELDS:
            field_report[std_name] = "missing"

        for col in fieldnames:
            col_clean = col.strip()
            matched = False
            for std_name, aliases in INPUT_FIELD_ALIASES.items():
                if col_clean == std_name or col_clean in aliases:
                    header_map[col_clean] = std_name
                    field_report[std_name] = "found"
                    matched = True
                    break
            if not matched:
                # 未知字段 → 保留原名（可能是自定义字段）
                header_map[col_clean] = col_clean

        # 对未找到的标准字段，尝试用标准名本身匹配
        for std_name in ALL_STANDARD_FIELDS:
            if field_report.get(std_name) == "missing" and std_name in header_map:
                field_report[std_name] = "found"

        return header_map, field_report

    def _map_row(self, row: dict, header_map: dict) -> tuple[dict, list[dict]]:
        """将原始行映射为标准字段，返回 (映射结果, 降级警告列表)"""
        mapped = {}
        warnings = []

        # 先映射所有列
        for col, val in row.items():
            std = header_map.get(col.strip(), col.strip())
            mapped[std] = (val or "").strip()

        # 降级字段处理
        for field, config in DEGRADABLE_FIELDS.items():
            if field not in header_map.values():
                # 该字段在 CSV 中根本不存在
                mapped[field] = config["default"]
                warnings.append({
                    "field": field,
                    "warning": f"文件中无 '{field}' 列，{config['warning']}",
                })
            elif not mapped.get(field):
                # 字段存在但值为空
                mapped[field] = config["default"]
                warnings.append({
                    "field": field,
                    "warning": f"'{field}' 值为空，{config['warning']}",
                })

        # 数值字段处理
        for field, default in NUMERIC_FIELDS.items():
            raw = mapped.get(field, "")
            if not raw:
                mapped[field] = str(default)
            else:
                try:
                    int(raw)
                except ValueError:
                    mapped[field] = str(default)
                    warnings.append({
                        "field": field,
                        "warning": f"'{field}' 值 '{raw}' 非有效数字，降级为 {default}",
                    })

        # 可选字段补默认值
        for field in OPTIONAL_FIELDS:
            if field not in mapped:
                mapped[field] = ""

        return mapped, warnings

    def _check_uniqueness(self, result: ReadResult) -> ReadResult:
        """检查 error_id 唯一性，重复的条目标记为阻断"""
        seen = {}
        for item in result.errors:
            eid = item.error_code or ""
            if eid and eid in seen:
                result.duplicate_ids.append(eid)
                # 不跳过，后续 input_validator 会根据重复标记处理
            elif eid:
                seen[eid] = True
        return result


# ── 便利函数 ──

def read_input(filepath: str = "") -> ReadResult:
    """读取默认路径的报错文件"""
    adapter = FileInputAdapter()
    path = filepath or adapter.default_path
    return adapter.read(path)


def read_and_standardize(filepath: str = "", run_id: str = "") -> ReadResult:
    """读取并输出标准化 CSV"""
    adapter = FileInputAdapter()
    path = filepath or adapter.default_path
    result = adapter.read(path)
    if result.success and result.errors:
        adapter.write_standardized(result, run_id or _default_run_id())
    return result


def _default_run_id() -> str:
    return f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
