from fastapi import APIRouter, HTTPException, Path

from app.schemas.provider import (
    ProviderSummaryResponse,
    ProviderUpsertRequest,
)
from llm_providers.base import ModelError, ProviderNotFoundError
from llm_providers.config import ProviderConfig
from llm_providers.registry import (
    add_provider,
    list_provider_summaries,
    list_providers,
    remove_provider,
    update_provider,
)

router = APIRouter(tags=["providers"])


@router.get("/providers", response_model=list[ProviderSummaryResponse])
async def get_providers() -> list[ProviderSummaryResponse]:
    providers = await list_provider_summaries()
    return [ProviderSummaryResponse.model_validate(provider.model_dump()) for provider in providers]


@router.post("/providers", response_model=ProviderSummaryResponse)
async def create_provider(request: ProviderUpsertRequest) -> ProviderSummaryResponse:
    config = _to_provider_config(request)
    try:
        await add_provider(config)
    except ModelError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ProviderSummaryResponse.model_validate(
        {
            **config.model_dump(exclude={"api_key"}),
            "has_api_key": config.api_key is not None,
        }
    )


@router.put("/providers/{provider_name}", response_model=ProviderSummaryResponse)
async def edit_provider(
    request: ProviderUpsertRequest,
    provider_name: str = Path(..., min_length=1),
) -> ProviderSummaryResponse:
    if request.name != provider_name:
        raise HTTPException(status_code=400, detail="Provider name cannot be changed")

    existing = {provider.name: provider for provider in await list_providers()}
    if provider_name not in existing:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_name}")

    previous = existing[provider_name]
    api_key = request.api_key
    if request.clear_api_key:
        api_key = None
    elif api_key is None:
        api_key = previous.api_key.get_secret_value() if previous.api_key is not None else None

    config = _to_provider_config(request, api_key=api_key)
    try:
        await update_provider(config)
    except ProviderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ProviderSummaryResponse.model_validate(
        {
            **config.model_dump(exclude={"api_key"}),
            "has_api_key": config.api_key is not None,
        }
    )


@router.delete("/providers/{provider_name}")
async def delete_provider(provider_name: str = Path(..., min_length=1)) -> dict[str, bool]:
    try:
        await remove_provider(provider_name)
    except ProviderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": True}


def _to_provider_config(
    request: ProviderUpsertRequest,
    api_key: str | None = None,
) -> ProviderConfig:
    return ProviderConfig(
        name=request.name,
        kind=request.kind,
        model=request.model,
        base_url=request.base_url,
        api_key=api_key if api_key is not None else request.api_key,
        api_key_header=request.api_key_header,
        is_default=request.is_default,
    )
