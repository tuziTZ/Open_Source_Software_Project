"""摘要步骤"""

from ..analysis.chunker import chunk_by_headings
from ..analysis.prompts import SUMMARY_PROMPTS
from ..analysis.strategies import select_strategy
from ..core.config import CHUNK_MAX_CHARS
from ..core.state import AgentState
from .base import BaseStep


class SummarizeStep(BaseStep):
    """执行摘要"""

    async def execute(self, state: AgentState, agent) -> AgentState:
        if not state.profile:
            from ..analysis.analyzer import analyze
            state.profile = analyze(state.content)

        strategy = select_strategy(state.profile)

        if strategy == "hierarchical":
            chunks = chunk_by_headings(state.content, CHUNK_MAX_CHARS)
            chunk_summaries = []
            for chunk in chunks:
                prompt = SUMMARY_PROMPTS["hierarchical"].format(content=chunk)
                summary = await agent.llm.chat(prompt)
                chunk_summaries.append(summary)
            prompt = SUMMARY_PROMPTS["merge"].format(
                chunk_summaries="\n".join(chunk_summaries)
            )
            state.summary = await agent.llm.chat(prompt)
        else:
            prompt = SUMMARY_PROMPTS["direct"].format(content=state.content)
            state.summary = await agent.llm.chat(prompt)

        state.step_history.append(f"summarize:{strategy}")
        return state
