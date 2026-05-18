from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/agents/summary", tags=["agent-summary"])


class SummaryRequest(BaseModel):
    entry_id: str
    target_lang: str = "en"


class SummaryResponse(BaseModel):
    entry_id: str
    summary: str


@router.post("/generate", response_model=SummaryResponse)
async def generate_summary(req: SummaryRequest):
    # Minimal mock implementation for integration and testing.
    # Replace with real agent orchestration that calls llm_providers.
    text = f"Mock summary for {req.entry_id} (lang={req.target_lang})"
    return SummaryResponse(entry_id=req.entry_id, summary=text)
