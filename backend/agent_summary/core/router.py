"""条件路由器"""

from collections.abc import Callable

from .state import AgentState


class Router:
    """根据状态决定下一步"""

    def __init__(self):
        self.routes: list[tuple[Callable[[AgentState], bool], str]] = []

    def add_route(self, condition: Callable[[AgentState], bool], step_name: str):
        """添加路由规则"""
        self.routes.append((condition, step_name))

    async def route(self, state: AgentState) -> str:
        """根据状态选择下一步"""
        for condition, step_name in self.routes:
            if condition(state):
                return step_name
        raise ValueError("No matching route")
