"""评估步骤"""

from ..core.config import EVAL_MIN_LENGTH
from ..core.state import AgentState
from .base import BaseStep


class EvaluateStep(BaseStep):
    """评估摘要质量"""

    async def execute(self, state: AgentState, agent) -> AgentState:
        # 简单检查：摘要长度是否合理
        if state.summary and len(state.summary) < EVAL_MIN_LENGTH:
            # 太短，重试一次
            from .summarize import SummarizeStep
            state = await SummarizeStep().execute(state, agent)
            state.step_history.append("evaluate:retry")
        else:
            state.step_history.append("evaluate:pass")
        return state
