"""钩子系统"""

from collections.abc import Callable
from typing import Any


class HookRegistry:
    """事件钩子"""

    def __init__(self):
        self._hooks: dict[str, list[Callable]] = {}

    def on(self, event: str, callback: Callable):
        """注册钩子"""
        self._hooks.setdefault(event, []).append(callback)

    async def emit(self, event: str, data: Any):
        """触发钩子"""
        for callback in self._hooks.get(event, []):
            if callable(callback):
                callback(data)
