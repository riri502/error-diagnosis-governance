"""全局配置 — 路径、阈值、权重"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据路径
DATA_INBOX = os.path.join(PROJECT_ROOT, "data", "inbox")
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")
DATA_SAMPLES = os.path.join(PROJECT_ROOT, "data", "samples")

# 知识库路径
KNOWLEDGE_BUSINESS = os.path.join(PROJECT_ROOT, "knowledge", "business")
KNOWLEDGE_DESIGN = os.path.join(PROJECT_ROOT, "knowledge", "design")
KNOWLEDGE_CASES = os.path.join(PROJECT_ROOT, "knowledge", "cases_confirmed")

# 产出物路径
ARTIFACTS_DIAGNOSIS = os.path.join(PROJECT_ROOT, "artifacts", "diagnosis_reports")
ARTIFACTS_REVIEW_CARDS = os.path.join(PROJECT_ROOT, "artifacts", "review_cards")

# 状态路径
STATE_LEDGER = os.path.join(PROJECT_ROOT, "state", "governance_ledger.csv")
STATE_EVIDENCE = os.path.join(PROJECT_ROOT, "state", "evidence_registry.csv")
STATE_ISSUE_POOLS = os.path.join(PROJECT_ROOT, "state", "issue_pools")

# 规则路径
RULES_DIR = os.path.join(PROJECT_ROOT, "rules")

# 输入字段映射（标准名 → 别名列表）
INPUT_FIELD_ALIASES = {
    "error_code": ["错误码", "code", "报错码", "errorCode"],
    "error_message": ["报错提示", "error_msg", "报错文案", "错误提示", "errorMessage"],
    "url": ["页面URL", "请求URL", "链接", "访问URL"],
    "page_route": ["路由", "页面路由", "页面路径", "路径", "pageRoute"],
    "trigger_scenario": ["触发场景", "triggerScenario"],
    "error_count": ["页面报错次数", "报错次数", "errorCount", "次数"],
}

# 必填字段
REQUIRED_FIELDS = ["error_message"]

# 优先级评分权重（DOC-04）
PRIORITY_WEIGHTS = {
    "journey_impact": 0.25,
    "experience_violation": 0.20,
    "customer_impact": 0.20,
    "error_scale": 0.20,
    "fix_feasibility": 0.15,
}

# 置信度阈值
LOW_CONFIDENCE_THRESHOLD = 0.4  # 低于此值 → 低置信诊断池

# 优先级定级
PRIORITY_THRESHOLDS = [
    (80, "P0"),
    (60, "P1"),
    (40, "P2"),
    (0, "P3"),
]

# 状态枚举
STATUS_PENDING = "待评估"
STATUS_DIAGNOSING = "诊断中"
STATUS_WAITING_HUMAN = "待人工复核"
STATUS_REVIEWED = "人工复核完成"
STATUS_ARCHIVED = "已归档"

# 人工复核结论枚举
REVIEW_CONCLUSIONS = [
    "评估准确，进入治理",
    "评估基本准确，需调整建议",
    "评估不准确",
    "条目暂未复现",
    "条目无需优化",
    "需补充信息",
    "需产品确认",
    "需研发确认",
    "需补充埋点",
]
