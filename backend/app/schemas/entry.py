from pydantic import BaseModel

from app.schemas.common import LongTaskStatus


class Entry(BaseModel):
    id: str
    feed_id: str
    title: str
    summary: str
    author: str
    url: str
    published_at: str
    is_read: bool
    is_starred: bool
    tag_ids: list[str]
    reader_html: str
    web_preview: str
    related_entry_ids: list[str]
    note: str
    summary_text: str
    translation_html: str | None = None
    translation_status: LongTaskStatus
