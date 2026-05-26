"""翻译步骤"""

from ..core.state import AgentState
from .base import BaseStep


class TranslateStep(BaseStep):
    """调用翻译 Agent"""

    async def execute(self, state: AgentState, agent, target_lang: str = "zh") -> AgentState:
        translate_tool = agent.tools.get("call_translation")

        if translate_tool:
            from ..tools.base import invoke_tool_with_retry
            translation = await invoke_tool_with_retry(
                translate_tool,
                entry_id=state.entry_id,
                target_lang=target_lang,
            )
            state.metadata["translation"] = translation
            state.step_history.append(f"translate:{target_lang}")
        else:
            state.step_history.append("translate:no_tool")

        return state
