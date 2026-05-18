from pydantic import BaseModel

from app.schemas.common import LongTaskStatus


class SummaryRequest(BaseModel):
    entry_id: str
    provider: str | None = None
    model: str | None = None


class SummaryResult(BaseModel):
    entry_id: str
    summary_text: str
    status: LongTaskStatus
    provider: str
    model: str


class TranslationRequest(BaseModel):
    entry_id: str
    target_lang: str
    provider: str | None = None
    model: str | None = None


class TranslationResult(BaseModel):
    entry_id: str
    target_lang: str
    translation_html: str
    status: LongTaskStatus
    provider: str
    model: str
