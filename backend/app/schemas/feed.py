from pydantic import BaseModel

from app.schemas.common import LongTaskStatus


class Feed(BaseModel):
    id: str
    title: str
    site_url: str
    feed_url: str
    unread_count: int
    status: LongTaskStatus
