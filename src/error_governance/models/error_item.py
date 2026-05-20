"""报错条目模型"""

from typing import Optional
from pydantic import BaseModel, Field


class ErrorItem(BaseModel):
    """单条报错输入"""
    error_code: Optional[str] = Field(default=None, alias="错误码")
    error_message: str = Field(alias="报错提示")
    url: Optional[str] = Field(default=None, alias="URL")
    page_route: Optional[str] = Field(default=None, alias="页面路由")
    trigger_scenario: Optional[str] = Field(default=None, alias="触发场景")
    error_count: int = Field(default=1, alias="页面报错次数")

    class Config:
        populate_by_name = True


class ErrorFeatures(BaseModel):
    """报错特征（DOC-01 分类结果）"""
    major_category: str = ""
    minor_category: str = ""
    task_type: str = ""
    validation_logic: str = ""
    error_reason: str = ""
    business_module: str = ""
    search_keywords: list[str] = []
