"""HTTP routes for translation agent requests."""

from fastapi import APIRouter, HTTPException

from app.schemas.agent import TranslationRequest, TranslationResult

from ..service import (
    ArticleContentUnavailableError,
    ArticleNotFoundError,
    TranslationService,
)

router = APIRouter(prefix="/agents/translation", tags=["agent-translation"])


def get_translation_service() -> TranslationService:
    return TranslationService()


@router.post("", response_model=TranslationResult)
async def translate_article(request: TranslationRequest) -> TranslationResult:
    """
    Translate an article to the target language.

    Args:
        request: TranslationRequest with entry_id, target_lang, provider, model

    Returns:
        TranslationResult with translated_html and status

    Raises:
        404: If article not found
        409: If article has no content to translate
    """
    service = get_translation_service()
    try:
        return await service.generate(request)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Entry not found") from exc
    except ArticleContentUnavailableError as exc:
        raise HTTPException(status_code=409, detail="Entry has no content to translate") from exc
