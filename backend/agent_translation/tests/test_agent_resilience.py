"""Tests for TranslationAgent chunk-level resilience.

A single failing chunk must not sink the whole article: the agent retries,
then falls back to the original text for that chunk. Only when every chunk
fails does the agent raise so the service can mark the request as failed.
"""

import pytest

from agent_translation.agent import TranslationAgent
from llm_providers.base import (
    ChatCompletion,
    ChatMessage,
    ChatOptions,
    LLMProviderError,
    NetworkError,
    TokenUsage,
)


class FakeProvider:
    """Provider stub whose chat() outcome is scripted per call."""

    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-model"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        options: ChatOptions | None = None,
    ) -> ChatCompletion:
        outcome = self._outcomes[min(self.calls, len(self._outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return ChatCompletion(
            content=outcome,
            model=self.model,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1),
        )


@pytest.mark.asyncio
async def test_chunk_retries_then_succeeds() -> None:
    # First attempt fails, retry succeeds -> single chunk translated.
    provider = FakeProvider([NetworkError("boom"), "你好"])
    agent = TranslationAgent(provider=provider)

    result = await agent.translate("Hello world", target_lang="中文")

    assert provider.calls == 2
    assert "你好" in result["translated_text"]


@pytest.mark.asyncio
async def test_all_chunks_failing_raises() -> None:
    # When every chunk fails after retries, the agent raises so the service
    # can mark the whole request as failed (rather than returning garbage).
    content = "# Heading\n\nFirst paragraph here.\n\n" + ("x" * 600) + "\n\nSecond block."
    provider = FakeProvider([NetworkError("down")])  # every call fails
    agent = TranslationAgent(provider=provider)

    with pytest.raises(LLMProviderError):
        await agent.translate(content, target_lang="中文")


@pytest.mark.asyncio
async def test_single_chunk_failure_does_not_abort_when_others_succeed() -> None:
    # Script: chunk 1 fails 3x (retries) then we move on; chunk 2 succeeds.
    # Use bilingual=False path with two chunks split by headings.
    content = "# Title A\n\n" + ("a" * 4100) + "\n\n# Title B\n\nBody."
    # Each translate_chunk does up to 3 attempts. First chunk: 3 failures.
    # Remaining calls succeed.
    outcomes: list[object] = [
        NetworkError("1"),
        NetworkError("2"),
        NetworkError("3"),
        "translated",
    ]
    provider = FakeProvider(outcomes)
    agent = TranslationAgent(provider=provider)

    result = await agent.translate(content, target_lang="中文")

    # The article still returns; the failed chunk falls back to its original text.
    assert "translated" in result["translated_text"]
    assert result["provider"] == "fake"
