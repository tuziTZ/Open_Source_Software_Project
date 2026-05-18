from pydantic import BaseModel


class DigestTemplate(BaseModel):
    id: str
    title: str
    include_summary: bool
    include_notes: bool
    include_tags: bool
