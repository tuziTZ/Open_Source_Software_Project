"""SummaryAgent 核心实现"""

from time import time

from ..core.hooks import HookRegistry
from ..core.router import Router
from ..core.state import AgentState
from ..core.tracer import RunResult
from ..llm_client import LLMClient
from ..steps.analyze import AnalyzeStep
from ..steps.evaluate import EvaluateStep
from ..steps.search import SearchStep
from ..steps.summarize import SummarizeStep
from ..tools.base import Tool, ToolRegistry


class MockLLM:
    """Mock LLM 用于测试"""

    async def chat(self, prompt: str) -> str:
        return f"Mock summary for: {prompt[:50]}..."


class SummaryAgent:
    """摘要 Agent"""

    def __init__(self, llm_provider=None, tools: list[Tool] | None = None, use_mock: bool = False):
        # 默认使用真实 LLM，测试时可传入 use_mock=True
        if llm_provider:
            self.llm = llm_provider
        elif use_mock:
            self.llm = MockLLM()
        else:
            self.llm = LLMClient()

        self.tools = ToolRegistry()
        self.hooks = HookRegistry()
        self.router = Router()

        # 注册工具
        for t in (tools or []):
            self.tools.register(t)

        # 配置路由
        self._setup_routes()

    def _setup_routes(self):
        """配置条件路由"""
        self.router.add_route(
            lambda s: s.profile is not None and s.profile.needs_context,
            "search"
        )
        self.router.add_route(
            lambda s: s.profile is not None and s.profile.length > 8000,
            "hierarchical"
        )
        self.router.add_route(lambda s: True, "direct")

    async def run(self, state: AgentState) -> tuple[AgentState, RunResult]:
        """执行 Agent"""
        start_time = time()
        tool_calls = []

        # 1. 分析
        await self.hooks.emit("before_analyze", state)
        state = await AnalyzeStep().execute(state, self)
        await self.hooks.emit("after_analyze", state)

        # 2. 路由
        next_step = await self.router.route(state)
        state.step_history.append(f"route:{next_step}")

        # 3. 执行搜索（如果需要）
        if next_step == "search":
            state = await SearchStep().execute(state, self)

        # 4. 摘要
        state = await SummarizeStep().execute(state, self)

        # 5. 评估
        state = await EvaluateStep().execute(state, self)

        return state, RunResult(
            output=state.summary or "",
            steps=state.step_history,
            tool_calls=tool_calls,
            total_duration=time() - start_time,
            token_usage=state.metadata.get("usage", {}),
        )

    async def summarize(self, entry_id: str, content: str) -> dict:
        """主入口"""
        state = AgentState(entry_id=entry_id, content=content)
        state, result = await self.run(state)

        return {
            "entry_id": entry_id,
            "summary_text": state.summary or "",
            "status": "success",
            "provider": "ecnu",
            "model": "ecnu-max",
            "steps": result.steps,
            "duration": result.total_duration,
        }
