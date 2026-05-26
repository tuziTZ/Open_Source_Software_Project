"""测试核心层"""

import pytest

from agent_summary.core.config import CHUNK_MAX_CHARS, PROMPT_VERSION
from agent_summary.core.router import Router
from agent_summary.core.state import AgentState, ArticleProfile


class TestArticleProfile:
    """测试 ArticleProfile"""

    def test_creation(self):
        profile = ArticleProfile(
            language="zh",
            length=1000,
            has_headings=True,
            article_type="blog",
            section_count=3,
            needs_context=False,
        )
        assert profile.language == "zh"
        assert profile.length == 1000
        assert profile.has_headings is True

    def test_serialization(self):
        profile = ArticleProfile(
            language="en",
            length=500,
            has_headings=False,
            article_type="news",
            section_count=0,
            needs_context=True,
        )
        data = profile.model_dump()
        assert data["language"] == "en"
        assert data["needs_context"] is True


class TestAgentState:
    """测试 AgentState"""

    def test_defaults(self):
        state = AgentState(entry_id="test-1", content="Hello World")
        assert state.entry_id == "test-1"
        assert state.summary is None
        assert state.profile is None
        assert state.search_results == []
        assert state.step_history == []

    def test_with_profile(self):
        profile = ArticleProfile(
            language="zh",
            length=100,
            has_headings=False,
            article_type="blog",
            section_count=0,
            needs_context=False,
        )
        state = AgentState(
            entry_id="test-2",
            content="Test content",
            profile=profile,
        )
        assert state.profile.language == "zh"


class TestRouter:
    """测试 Router"""

    @pytest.mark.anyio
    async def test_matches_first_condition(self):
        router = Router()
        router.add_route(lambda s: s.entry_id == "match", "first")
        router.add_route(lambda s: True, "default")

        state = AgentState(entry_id="match", content="test")
        result = await router.route(state)
        assert result == "first"

    @pytest.mark.anyio
    async def test_matches_default(self):
        router = Router()
        router.add_route(lambda s: s.entry_id == "no_match", "first")
        router.add_route(lambda s: True, "default")

        state = AgentState(entry_id="other", content="test")
        result = await router.route(state)
        assert result == "default"

    @pytest.mark.anyio
    async def test_raises_on_no_match(self):
        router = Router()
        router.add_route(lambda s: False, "first")

        state = AgentState(entry_id="test", content="test")
        with pytest.raises(ValueError, match="No matching route"):
            await router.route(state)


class TestConfig:
    """测试配置"""

    def test_prompt_version(self):
        assert PROMPT_VERSION == "v1"

    def test_chunk_max_chars(self):
        assert CHUNK_MAX_CHARS == 4000
