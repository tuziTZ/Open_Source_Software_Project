"""HTTP routes for LLM provider management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, SecretStr

from llm_providers import (
    ProviderConfig,
    ProviderKind,
    ProviderSummary,
    add_provider,
    get_provider,
    list_provider_summaries,
    list_providers,
    remove_provider,
    update_provider,
)
from llm_providers.base import LLMProviderError, ProviderNotFoundError

router = APIRouter(prefix="/providers", tags=["providers"])


class SetDefaultRequest(BaseModel):
    name: str


class CreateProviderRequest(BaseModel):
    name: str
    kind: str = "openai_compatible"
    model: str = ""
    base_url: str | None = None
    api_key: str | None = None
    api_key_header: str | None = None
    is_default: bool = False


class UpdateProviderRequest(BaseModel):
    name: str
    kind: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    api_key_header: str | None = None
    is_default: bool | None = None


@router.get("/", response_model=list[ProviderSummary])
async def get_providers() -> list[ProviderSummary]:
    """获取所有提供商列表（不包含敏感信息）"""
    return await list_provider_summaries()


@router.get("/{name}", response_model=ProviderSummary | None)
async def get_provider_by_name(name: str) -> ProviderSummary | None:
    """获取指定提供商"""
    summaries = await list_provider_summaries()
    for provider in summaries:
        if provider.name == name:
            return provider
    return None


@router.get("/default", response_model=ProviderSummary | None)
async def get_default_provider() -> ProviderSummary | None:
    """获取默认提供商"""
    summaries = await list_provider_summaries()
    for provider in summaries:
        if provider.is_default:
            return provider
    return summaries[0] if summaries else None


def _validate_header_value(value: str | None) -> str | None:
    """验证 header 值只包含 ASCII 字符"""
    if value is None or value.strip() == "":
        return None
    # 只保留 ASCII 字符
    cleaned = value.encode("ascii", errors="ignore").decode("ascii")
    return cleaned if cleaned.strip() else None


@router.post("/")
async def create_provider(request: CreateProviderRequest) -> dict:
    """创建新的提供商"""
    try:
        # 转换 kind 字符串为 ProviderKind 枚举
        kind_map = {
            "openai_compatible": ProviderKind.OPENAI_COMPATIBLE,
            "anthropic": ProviderKind.ANTHROPIC,
            "ollama": ProviderKind.OLLAMA,
        }
        kind = kind_map.get(request.kind, ProviderKind.OPENAI_COMPATIBLE)

        # 验证 api_key_header
        api_key_header = _validate_header_value(request.api_key_header)

        # 构建 ProviderConfig
        config = ProviderConfig(
            name=request.name,
            kind=kind,
            model=request.model,
            base_url=request.base_url,
            api_key=SecretStr(request.api_key) if request.api_key else None,
            api_key_header=api_key_header,
            is_default=request.is_default,
        )

        await add_provider(config)
        return {"status": "ok", "name": request.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{name}")
async def update_provider_by_name(name: str, request: UpdateProviderRequest) -> dict:
    """更新提供商配置"""
    try:
        # 获取现有配置
        providers = await list_providers()
        existing = None
        for provider in providers:
            if provider.name == name:
                existing = provider
                break

        if existing is None:
            raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")

        # 转换 kind 字符串为 ProviderKind 枚举
        kind_map = {
            "openai_compatible": ProviderKind.OPENAI_COMPATIBLE,
            "anthropic": ProviderKind.ANTHROPIC,
            "ollama": ProviderKind.OLLAMA,
        }

        # 构建更新后的配置
        kind = (
            kind_map.get(request.kind, existing.kind)
            if request.kind
            else existing.kind
        )
        api_key_header = (
            _validate_header_value(request.api_key_header)
            if request.api_key_header is not None
            else existing.api_key_header
        )
        is_default = (
            request.is_default
            if request.is_default is not None
            else existing.is_default
        )
        config = ProviderConfig(
            name=name,
            kind=kind,
            model=request.model if request.model is not None else existing.model,
            base_url=request.base_url if request.base_url is not None else existing.base_url,
            api_key=SecretStr(request.api_key) if request.api_key else existing.api_key,
            api_key_header=api_key_header,
            is_default=is_default,
        )

        await update_provider(config)
        return {"status": "ok", "name": name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/default")
async def set_default_provider(request: SetDefaultRequest) -> dict:
    """设置默认提供商"""
    try:
        providers = await list_providers()
        updated = []
        for provider in providers:
            if provider.name == request.name:
                updated.append(provider.model_copy(update={"is_default": True}))
            else:
                updated.append(provider.model_copy(update={"is_default": False}))

        # 保存更新后的配置
        from llm_providers.config import ProvidersFile, save_providers_file
        from llm_providers.registry import resolved_config_path
        save_providers_file(resolved_config_path(), ProvidersFile(providers=updated))

        return {"status": "ok", "default": request.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{name}")
async def delete_provider(name: str) -> dict:
    """删除提供商"""
    try:
        await remove_provider(name)
        return {"status": "ok", "name": name}
    except ProviderNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{name}' not found"
        ) from exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/test/{name}")
async def test_provider(name: str) -> dict:
    """测试提供商连接"""
    try:
        provider = get_provider(name)
        from llm_providers import ChatMessage
        messages = [ChatMessage(role="user", content="Say 'ok' in one word.")]
        result = await provider.chat(messages)
        return {
            "status": "ok",
            "provider": name,
            "model": provider.model,
            "response": result.content[:50]
        }
    except ProviderNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{name}' not found"
        ) from exc
    except LLMProviderError as e:
        return {"status": "error", "provider": name, "error": str(e)}
    except Exception as e:
        return {"status": "error", "provider": name, "error": str(e)}
