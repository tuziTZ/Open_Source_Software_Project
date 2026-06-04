"""HTTP routes for translation agent requests.

Endpoints:
- POST /agents/translation - Translate an article
- GET /agents/translation/{entry_id} - Get cached translation (future)

Errors are returned as 4xx/5xx HTTP status codes per the contract.
When translation fails, a 200 response with FAILURE status is returned instead.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.agent import TranslationRequest, TranslationResult

from ..service import (
    ArticleContentUnavailableError,
    ArticleNotFoundError,
    TranslationService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/translation", tags=["agent-translation"])


def get_translation_service() -> TranslationService:
    """Factory for TranslationService instances."""
    return TranslationService()


@router.post("", response_model=TranslationResult)
async def translate_article(request: TranslationRequest) -> TranslationResult:
    """
    Translate an article to the target language.

    The translation is performed using the specified (or default) LLM provider.
    Results are persisted to the database.

    Request:
        {
          "entry_id": "article-123",
          "target_lang": "English",
          "provider": "openai",        # optional, uses default if not specified
          "model": "gpt-4"             # optional, uses provider default if not specified
        }

    Response on success (200):
        {
          "entry_id": "article-123",
          "target_lang": "English",
          "translation_html": "Translated content...",
          "status": "success",
          "provider": "openai",
          "model": "gpt-4"
        }

    Response on translation failure (200 with status: failure):
        {
          "entry_id": "article-123",
          "target_lang": "English",
          "translation_html": "",
          "status": "failure",
          "provider": "openai",
          "model": "gpt-4"
        }

    Error responses:
        404: Article not found
        409: Article has no content to translate

    Args:
        request: TranslationRequest with entry_id, target_lang, provider, model

    Returns:
        TranslationResult with translated content and status

    Raises:
        HTTPException 404: If article doesn't exist
        HTTPException 409: If article has no content
    """
    service = get_translation_service()

    try:
        return await service.generate(request)

    except ArticleNotFoundError as exc:
        logger.warning(f"Translation request for missing article: {request.entry_id}")
        raise HTTPException(status_code=404, detail="Entry not found") from exc

    except ArticleContentUnavailableError as exc:
        logger.warning(f"Translation request for article without content: {request.entry_id}")
        raise HTTPException(status_code=409, detail="Entry has no content to translate") from exc
