"""执行追踪"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCallRecord:
    """工具调用记录"""
    tool_name: str
    arguments: dict
    result: Any
    duration: float
    error: str | None = None


@dataclass
class RunResult:
    """执行结果"""
    output: str
    steps: list[str]
    tool_calls: list[ToolCallRecord]
    total_duration: float
    token_usage: dict[str, int]
