"""分析步骤"""

from ..analysis.analyzer import analyze
from ..core.state import AgentState
from .base import BaseStep


class AnalyzeStep(BaseStep):
    """分析文章"""

    async def execute(self, state: AgentState, agent) -> AgentState:
        state.profile = analyze(state.content)
        state.step_history.append("analyze")
        return state
