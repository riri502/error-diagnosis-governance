"""全局配置"""

import os

SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(SRC_ROOT)

# 数据路径
DATA_INBOX = os.path.join(PROJECT_ROOT, "data", "inbox")
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")

# 知识库
KNOWLEDGE_BUSINESS = os.path.join(PROJECT_ROOT, "knowledge", "business")
KNOWLEDGE_DESIGN = os.path.join(PROJECT_ROOT, "knowledge", "design")
KNOWLEDGE_CASES = os.path.join(PROJECT_ROOT, "knowledge", "cases_confirmed")

# 产出物
ARTIFACTS_DIAGNOSIS = os.path.join(PROJECT_ROOT, "artifacts", "diagnosis_reports")
ARTIFACTS_REVIEW_CARDS = os.path.join(PROJECT_ROOT, "artifacts", "review_cards")
ARTIFACTS_HUMAN_QUESTIONS = os.path.join(PROJECT_ROOT, "artifacts", "human_questions")
ARTIFACTS_RUN_LOGS = os.path.join(PROJECT_ROOT, "artifacts", "run_logs")

# 状态
STATE_LEDGER = os.path.join(PROJECT_ROOT, "state", "governance_ledger.csv")
STATE_EVIDENCE = os.path.join(PROJECT_ROOT, "state", "evidence_registry.csv")
STATE_ISSUE_POOLS = os.path.join(PROJECT_ROOT, "state", "issue_pools")
STATE_RUNS = os.path.join(PROJECT_ROOT, "state", "runs")

# 规则
RULES_DIR = os.path.join(PROJECT_ROOT, "rules")

# 输入字段别名映射
INPUT_FIELD_ALIASES = {
    "error_code": ["错误码", "code", "报错码", "errorCode"],
    "error_message": ["报错提示", "error_msg", "报错文案", "错误提示", "errorMessage"],
    "url": ["页面URL", "请求URL", "链接", "访问URL"],
    "page_route": ["路由", "页面路由", "页面路径", "路径", "pageRoute"],
    "trigger_scenario": ["触发场景", "triggerScenario"],
    "error_count": ["页面报错次数", "报错次数", "errorCount", "次数"],
}

REQUIRED_FIELDS = ["error_message"]

# 优先级权重 (DOC-04)
PRIORITY_WEIGHTS = {
    "journey_impact": 0.25,
    "experience_violation": 0.20,
    "customer_impact": 0.20,
    "error_scale": 0.20,
    "fix_feasibility": 0.15,
}

LOW_CONFIDENCE_THRESHOLD = 0.4
PRIORITY_THRESHOLDS = [(80, "P0"), (60, "P1"), (40, "P2"), (0, "P3")]

# 状态枚举 — 已迁移至 error_governance.models.workflow_state
# 保留别名以兼容旧引用（逐步迁移后删除）
from error_governance.models.workflow_state import ErrorItemStatus, RunStatus
STATUS_PENDING = ErrorItemStatus.PENDING.value
STATUS_DIAGNOSING = ErrorItemStatus.DIAGNOSING.value
STATUS_WAITING_HUMAN = ErrorItemStatus.WAITING_HUMAN.value
STATUS_REVIEWED = ErrorItemStatus.REVIEWED.value
STATUS_ARCHIVED = ErrorItemStatus.COMPLETED.value

HUMAN_REVIEW_CONCLUSIONS = [
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
