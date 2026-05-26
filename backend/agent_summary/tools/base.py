"""工具基础设施"""

import asyncio
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..core.config import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: dict
    func: Callable
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout: float = DEFAULT_TIMEOUT


def tool(func=None, *, name=None, description=None):
    """装饰器：自动从函数签名生成工具定义"""
    def decorator(f):
        desc = description or inspect.getdoc(f) or ""
        sig = inspect.signature(f)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            param_type = param.annotation
            if param_type is str:
                properties[param_name] = {"type": "string"}
            elif param_type is int:
                properties[param_name] = {"type": "integer"}
            elif param_type is float:
                properties[param_name] = {"type": "number"}
            elif param_type is bool:
                properties[param_name] = {"type": "boolean"}
            else:
                properties[param_name] = {"type": "string"}

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        f._tool_meta = Tool(
            name=name or f.__name__,
            description=desc,
            parameters={"type": "object", "properties": properties, "required": required},
            func=f,
        )
        return f

    if func is not None:
        return decorator(func)
    return decorator


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """返回工具列表"""
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self._tools.values()
        ]


async def invoke_tool_with_retry(tool: Tool, **kwargs) -> Any:
    """带重试和超时的工具调用"""
    for attempt in range(tool.max_retries):
        try:
            result = await asyncio.wait_for(tool.func(**kwargs), timeout=tool.timeout)
            return result
        except TimeoutError:
            if attempt == tool.max_retries - 1:
                raise
        except Exception:
            if attempt == tool.max_retries - 1:
                raise
