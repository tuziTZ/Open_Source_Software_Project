from pydantic import BaseModel

from llm_providers.config import ProviderKind


class ProviderSummaryResponse(BaseModel):
    name: str
    kind: ProviderKind
    model: str
    base_url: str | None = None
    api_key_header: str | None = None
    is_default: bool = False
    has_api_key: bool = False


class ProviderUpsertRequest(BaseModel):
    name: str
    kind: ProviderKind
    model: str
    base_url: str | None = None
    api_key: str | None = None
    api_key_header: str | None = None
    is_default: bool = False
    clear_api_key: bool = False
