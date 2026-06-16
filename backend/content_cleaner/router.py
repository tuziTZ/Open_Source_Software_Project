from fastapi import APIRouter

from .schemas import CleanContentRequest, CleanContentResponse, WebPageResponse
from .service import clean_html, clean_stored_article, fetch_entry_web_page

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/clean", response_model=CleanContentResponse)
async def clean_content(request: CleanContentRequest) -> CleanContentResponse:
    return clean_html(request)


@router.get("/entries/{article_id}/clean", response_model=CleanContentResponse)
async def clean_stored_content(article_id: str) -> CleanContentResponse:
    return clean_stored_article(article_id)


@router.get("/entries/{article_id}/web", response_model=WebPageResponse)
async def fetch_stored_web_page(article_id: str) -> WebPageResponse:
    return fetch_entry_web_page(article_id)
