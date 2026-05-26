"""搜索步骤"""

from ..analysis.analyzer import extract_keywords
from ..core.state import AgentState
from .base import BaseStep


class SearchStep(BaseStep):
    """调用搜索工具"""

    async def execute(self, state: AgentState, agent) -> AgentState:
        if not state.profile or not state.profile.needs_context:
            state.step_history.append("search:skip")
            return state

        keywords = extract_keywords(state.content)
        search_tool = agent.tools.get("search_web")

        if search_tool:
            from ..tools.base import invoke_tool_with_retry
            results = await invoke_tool_with_retry(search_tool, query=" ".join(keywords))
            state.search_results = results
            state.step_history.append("search:execute")
        else:
            state.step_history.append("search:no_tool")

        return state
