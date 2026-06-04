"""Application service for article translation.

Responsible for:
1. Loading article content from database
2. Invoking translation agent with LLM provider
3. Handling errors and recording results
4. Persisting translations to database
"""

import re
from dataclasses import dataclass

from app.schemas.agent import TranslationRequest, TranslationResult
from app.schemas.common import LongTaskStatus
from db import get_article, get_article_content, record_usage, save_agent_result
from llm_providers import LLMProviderError, ProviderNotFoundError, get_provider

from .agent import TranslationAgent


class TranslationServiceError(Exception):
    """Base class for translation request failures."""


class ArticleNotFoundError(TranslationServiceError):
    """Raised when the requested article does not exist."""


class ArticleContentUnavailableError(TranslationServiceError):
    """Raised when the requested article has no usable content."""


@dataclass(slots=True)
class TranslationService:
    """
    Application service for article translation.

    Orchestrates:
    - Data loading from database
    - LLM provider selection
    - Translation execution
    - Result persistence
    - Usage tracking
    """

    async def generate(self, request: TranslationRequest) -> TranslationResult:
        """
        Generate translation for an article.

        Workflow:
        1. Load article metadata
        2. Resolve content (prefer cleaned over raw)
        3. Get LLM provider
        4. Execute translation
        5. Handle errors gracefully
        6. Save result and usage to database

        Args:
            request: TranslationRequest with entry_id, target_lang, provider, model

        Returns:
            TranslationResult with translated_html and status.
            Always succeeds - status indicates success/failure

        Raises:
            ArticleNotFoundError: If article doesn't exist
            ArticleContentUnavailableError: If article has no content
        """
        # 1. Load article from database
        article = get_article(request.entry_id)
        if article is None:
            raise ArticleNotFoundError(request.entry_id)

        # 2. Resolve content - prefer cleaned markdown/text over raw HTML
        content = self._resolve_content(request.entry_id, article.reader_html)
        if not content:
            raise ArticleContentUnavailableError(request.entry_id)

        # 3. Execute translation (with error handling)
        result = await self._execute_translation(
            entry_id=request.entry_id,
            target_lang=request.target_lang,
            content=content,
            provider_name=request.provider,
            model_name=request.model,
        )

        # 4. Save result to database
        save_agent_result(result)

        return result

    async def _execute_translation(
        self,
        entry_id: str,
        target_lang: str,
        content: str,
        provider_name: str | None,
        model_name: str | None,
    ) -> TranslationResult:
        """
        Execute translation with error handling.

        Returns SUCCESS or FAILURE status (never raises exceptions).
        Failures are recorded in the result for frontend handling.

        Args:
            entry_id: Article ID
            target_lang: Target language
            content: Article content to translate
            provider_name: Optional provider name (uses default if None)
            model_name: Optional model name (uses provider's default if None)

        Returns:
            TranslationResult with status SUCCESS or FAILURE
        """
        try:
            # Get LLM provider (uses default if name not specified)
            provider = get_provider(name=provider_name)

            # Build agent with selected provider
            agent = TranslationAgent(provider=provider)

            # Execute translation
            agent_result = await agent.translate(
                content=content,
                target_lang=target_lang,
                temperature=0.3,  # Lower temperature for consistency
            )

            # Record token usage
            record_usage(
                entry_id=entry_id,
                agent_type="translation",
                prompt_tokens=agent_result["usage"]["prompt_tokens"],
                completion_tokens=agent_result["usage"]["completion_tokens"],
                provider=agent_result["provider"],
                model=agent_result["model"],
            )

            # Return success result
            return TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html=agent_result["translated_text"],
                status=LongTaskStatus.SUCCESS,
                provider=agent_result["provider"],
                model=agent_result["model"],
            )

        except ProviderNotFoundError:
            # No provider configured
            return TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status=LongTaskStatus.FAILURE,
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )

        except LLMProviderError:
            # LLM API error (auth, network, rate limit, etc.)
            # Don't propagate - record as failure
            return TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status=LongTaskStatus.FAILURE,
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )

        except Exception:
            # Unexpected error - record as failure
            return TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status=LongTaskStatus.FAILURE,
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )

    def _resolve_content(self, entry_id: str, reader_html: str) -> str:
        """
        Resolve article content, preferring cleaned content over raw HTML.

        Content resolution priority:
        1. Cleaned markdown (highest quality)
        2. Plain text (fallback)
        3. Stripped raw HTML (last resort)

        Args:
            entry_id: Article ID for database lookup
            reader_html: Raw HTML from feed (fallback)

        Returns:
            Best available content string, or empty string if none available
        """
        # Try to get cleaned content from database
        stored_content = get_article_content(entry_id)
        if stored_content is not None:
            if stored_content.cleaned_markdown.strip():
                return stored_content.cleaned_markdown.strip()
            if stored_content.plain_text.strip():
                return stored_content.plain_text.strip()

        # Fallback: strip raw HTML
        if reader_html.strip():
            return self._strip_html(reader_html)

        return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        """
        Simple HTML tag removal.

        Removes HTML tags and normalizes whitespace.
        Used as fallback when cleaned content unavailable.

        Args:
            html: Raw HTML string

        Returns:
            Plain text with normalized whitespace
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()
