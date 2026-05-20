"""LLM 适配器（预留接口，不实现）"""

from error_governance.adapters.base_adapter import BaseLLMAdapter


class LLMAdapter(BaseLLMAdapter):
    """LLM 适配器 — 预留接口，后续可接入 OpenAI / 本地模型"""

    def __init__(self, model: str = ""):
        self.model = model

    def analyze(self, prompt: str, context: dict = {}) -> str:
        """Placeholder — 后续实现 LLM 调用"""
        raise NotImplementedError("LLM 适配器尚未实现")
