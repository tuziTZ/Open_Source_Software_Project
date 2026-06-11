from __future__ import annotations

import os
import re
from dataclasses import dataclass

from app.schemas.agent import SummaryRequest, SummaryResult
from db import get_article, get_article_content, save_agent_result
from llm_providers.base import ChatCompletion, ChatMessage, ProviderNotFoundError
from llm_providers.registry import _build_provider, _resolve_config_name, load_providers_from_config

from .agent.summary_agent import SummaryAgent
from .llm_client import LLMClient


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
        return summary

    def _build_agent(self, request: SummaryRequest) -> SummaryAgent:
        provider = (request.provider or "").strip().lower()
        use_mock = provider == "mock" or _use_mock_llm()
        if use_mock:
            return _instantiate_agent(self.agent_factory, use_mock=True)

        configured_provider = self._resolve_registered_provider(request)
        if configured_provider is not None:
            return _instantiate_agent(self.agent_factory, llm_provider=configured_provider)

        llm = LLMClient(model=request.model)
        return _instantiate_agent(self.agent_factory, llm_provider=llm)

    def _resolve_registered_provider(self, request: SummaryRequest):
        try:
            if request.provider is not None:
                config = _resolve_config_name(request.provider.strip())
            elif load_providers_from_config():
                config = _resolve_config_name(None)
            else:
                return None
        except ProviderNotFoundError:
            return None

        if request.model:
            config = config.model_copy(update={"model": request.model})

        provider = _build_provider(config)
        return _ProviderAdapter(provider.name, provider.model, provider)

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


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def _use_mock_llm() -> bool:
    if os.environ.get("LLM_API_KEY", "").strip():
        return False
    return os.environ.get("LLM_USE_MOCK", "true").strip().lower() in {"1", "true", "yes", "on"}


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
        response = await self._provider.chat([ChatMessage(role="user", content=prompt)])
        if isinstance(response, ChatCompletion):
            return response.content
        chunks = [chunk async for chunk in response]
        return "".join(chunks)
