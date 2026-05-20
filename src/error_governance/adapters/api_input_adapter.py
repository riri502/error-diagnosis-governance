"""API 输入适配器（预留，不实现真实对接）"""

from error_governance.adapters.base_adapter import BaseInputAdapter


class APIInputAdapter(BaseInputAdapter):
    """从 API 定时拉取报错数据 — 预留接口"""

    def __init__(self, endpoint: str = "", api_key: str = ""):
        self.endpoint = endpoint
        self.api_key = api_key

    def read_errors(self, source: str = "") -> list:
        """Placeholder — 后续实现 API 拉取逻辑"""
        raise NotImplementedError("API 输入适配器尚未实现，请使用 FileInputAdapter")
