"""步骤基类"""

from abc import ABC, abstractmethod

from ..core.state import AgentState


class BaseStep(ABC):
    """步骤基类"""

    @abstractmethod
    async def execute(self, state: AgentState, agent) -> AgentState:
        """执行步骤"""
        ...
