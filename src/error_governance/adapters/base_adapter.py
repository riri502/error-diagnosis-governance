"""适配器基类"""

from abc import ABC, abstractmethod


class BaseInputAdapter(ABC):
    """输入适配器基类"""

    @abstractmethod
    def read_errors(self, source: str) -> list:
        """读取报错数据，返回 ErrorItem 列表"""
        ...


class BaseEvidenceSource(ABC):
    """证据源基类"""

    @abstractmethod
    def is_available(self) -> bool:
        """数据源是否可用"""
        ...

    @abstractmethod
    def search(self, error_item, features) -> list:
        """检索证据，返回 EvidenceItem 列表"""
        ...


class BaseLLMAdapter(ABC):
    """LLM 适配器基类（预留）"""

    @abstractmethod
    def analyze(self, prompt: str, context: dict) -> str:
        ...
