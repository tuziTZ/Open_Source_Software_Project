from pydantic import BaseModel


class CleanContentRequest(BaseModel):
    raw_html: str
    source_url: str
    article_id: str | None = None
    content_hash: str | None = None


class CleanContentResponse(BaseModel):
    article_id: str | None = None
    cleaned_html: str
    cleaned_markdown: str
    plain_text: str
    content_hash: str | None = None
    word_count: int
    reading_time_minutes: int


class WebPageResponse(BaseModel):
    article_id: str
    url: str
    final_url: str
    content_type: str | None = None
    html: str
