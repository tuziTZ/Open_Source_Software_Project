from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC

from app.schemas.agent import SummaryRequest, SummaryResult
from db import get_article, get_article_content, record_usage, save_agent_result
from llm_providers import ChatMessage, get_provider
from llm_providers.base import LLMProvider

from .agent.summary_agent import SummaryAgent


class SummaryServiceError(Exception):
    """Base class for summary request failures."""


class ArticleNotFoundError(SummaryServiceError):
    """Raised when the requested article does not exist."""


class ArticleContentUnavailableError(SummaryServiceError):
    """Raised when the requested article has no usable content."""


@dataclass(slots=True)
class SummaryService:
    """Application service for loading article content and persisting summary results."""

    agent_factory: type[SummaryAgent] = SummaryAgent

    async def generate(self, request: SummaryRequest) -> SummaryResult:
        article = get_article(request.entry_id)
        if article is None:
            raise ArticleNotFoundError(request.entry_id)

        content = self._resolve_content(request.entry_id, article.reader_html)
        if not content:
            raise ArticleContentUnavailableError(request.entry_id)

        agent = self._build_agent(request)
        result = await agent.summarize(request.entry_id, content)
        summary = SummaryResult(
            entry_id=result["entry_id"],
            summary_text=result["summary_text"],
            status=result["status"],
            provider=result["provider"],
            model=result["model"],
        )
        save_agent_result(summary)

        # 记录 token 用量到 usage_buckets
        usage = result.get("usage", {})
        if usage:
            from datetime import datetime
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            record_usage(
                day=today,
                provider=result["provider"],
                model=result["model"],
                agent="summary",
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )

        return summary

    def _build_agent(self, request: SummaryRequest) -> SummaryAgent:
        provider_name = (request.provider or "").strip().lower()
        use_mock = provider_name == "mock" or _use_mock_llm()
        if use_mock:
            return _instantiate_agent(self.agent_factory, use_mock=True)

        # 使用 llm_providers registry 获取提供商
        provider = get_provider(request.provider if request.provider else None)
        # 如果请求指定了 model，创建一个包装器来覆盖默认 model
        if request.model:
            provider = ModelOverrideProvider(provider, request.model)
        return _instantiate_agent(self.agent_factory, llm_provider=provider)

    def _resolve_content(self, entry_id: str, reader_html: str) -> str:
        stored_content = get_article_content(entry_id)
        if stored_content is not None:
            if stored_content.cleaned_markdown.strip():
                return stored_content.cleaned_markdown.strip()
            if stored_content.plain_text.strip():
                return stored_content.plain_text.strip()

        if reader_html.strip():
            return _strip_html(reader_html)
        return ""


class ModelOverrideProvider:
    """包装 LLMProvider，允许覆盖默认 model 名称。"""

    def __init__(self, provider: LLMProvider, model: str):
        self._provider = provider
        self._model = model

    @property
    def name(self) -> str:
        return self._provider.name

    @property
    def model(self) -> str:
        return self._model

    async def chat(self, messages, *, stream=False, options=None):
        return await self._provider.chat(messages, stream=stream, options=options)


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def _use_mock_llm() -> bool:
    # 1. 如果环境变量明确设置了 LLM_USE_MOCK，使用它
    env_mock = os.environ.get("LLM_USE_MOCK", "").strip().lower()
    if env_mock in {"1", "true", "yes", "on"}:
        return True
    if env_mock in {"0", "false", "no", "off"}:
        return False

    # 2. 如果环境变量有 API Key，不使用 mock
    if os.environ.get("LLM_API_KEY", "").strip():
        return False

    # 3. 检查 providers.json 是否有配置
    try:
        from app.config import settings
        from llm_providers.config import load_providers_file, providers_path
        config = load_providers_file(providers_path(settings.data_dir))
        if config.providers:
            return False  # 有 provider 配置，不使用 mock
    except Exception:
        pass

    # 4. 默认使用 mock
    return True


def _instantiate_agent(agent_factory, **kwargs):
    try:
        return agent_factory(**kwargs)
    except TypeError:
        return agent_factory()


class _ProviderAdapter:
    def __init__(self, provider_name: str, model: str, provider) -> None:
        self.provider_name = provider_name
        self.model = model
        self._provider = provider

    async def chat(self, prompt: str) -> str:
        messages = [ChatMessage(role="user", content=prompt)]
        result = await self._provider.chat(messages)
        # ChatCompletion has .content attribute
        return result.content
