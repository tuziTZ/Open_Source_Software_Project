from fastapi import APIRouter

from .schemas import CleanContentRequest, CleanContentResponse
from .service import clean_html, clean_stored_article

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/clean", response_model=CleanContentResponse)
async def clean_content(request: CleanContentRequest) -> CleanContentResponse:
    return clean_html(request)


@router.get("/entries/{article_id}/clean", response_model=CleanContentResponse)
async def clean_stored_content(article_id: str) -> CleanContentResponse:
    return clean_stored_article(article_id)
