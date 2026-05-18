from pydantic import BaseModel


class Tag(BaseModel):
    id: str
    name: str
    aliases: list[str]
    usage_count: int
    unread_count: int
