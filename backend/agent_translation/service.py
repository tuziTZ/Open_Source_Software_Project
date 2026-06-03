"""Application service for article translation."""

from dataclasses import dataclass

from app.schemas.agent import TranslationRequest, TranslationResult
from app.schemas.common import LongTaskStatus
from db import get_article, get_article_content, save_agent_result


class TranslationServiceError(Exception):
    """Base class for translation request failures."""


class ArticleNotFoundError(TranslationServiceError):
    """Raised when the requested article does not exist."""


class ArticleContentUnavailableError(TranslationServiceError):
    """Raised when the requested article has no usable content."""


@dataclass(slots=True)
class TranslationService:
    """Application service for loading article content and persisting translation results."""

    async def generate(self, request: TranslationRequest) -> TranslationResult:
        """
        Generate translation for an article.

        Args:
            request: TranslationRequest with entry_id, target_lang, provider, model

        Returns:
            TranslationResult with translated_html and status

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

        # 3. TODO: Call translation agent (to be implemented)
        # translation_result = await self._translate(content, request.target_lang, request.provider, request.model)

        # 4. For now, return a placeholder result
        result = TranslationResult(
            entry_id=request.entry_id,
            target_lang=request.target_lang,
            translation_html="",  # TODO: Replace with actual translation
            status=LongTaskStatus.PENDING,
            provider=request.provider or "unknown",
            model=request.model or "unknown",
        )

        # 5. Save result to database
        save_agent_result(result)
        return result

    def _resolve_content(self, entry_id: str, reader_html: str) -> str:
        """
        Resolve article content, preferring cleaned content over raw HTML.

        Priority:
        1. Cleaned markdown
        2. Plain text
        3. Raw HTML
        """
        stored_content = get_article_content(entry_id)
        if stored_content is not None:
            if stored_content.cleaned_markdown.strip():
                return stored_content.cleaned_markdown.strip()
            if stored_content.plain_text.strip():
                return stored_content.plain_text.strip()

        if reader_html.strip():
            # Simple HTML stripping as fallback
            import re
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", reader_html)).strip()

        return ""
