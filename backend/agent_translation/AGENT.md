# agent_translation — 项目指南

**负责人**: 成员 7 (翻译工程师)

**状态**: MVP 实现完成，准备集成和测试

## 任务

将文章内容翻译为用户指定的目标语言，使用配置的大模型提供者。
提供一个简单的、与提供者无关的接口，支持任何 OpenAI 兼容 API、Anthropic Claude 或本地 Ollama 模型。
在 SQLite 中缓存翻译结果以供重复访问。

## 架构概览

```
前端 (Tauri)
    ↓ HTTP POST /agents/translation
    {
      "entry_id": "article-123",
      "target_lang": "英文",
      "provider": "openai",    # 可选
      "model": "gpt-4"         # 可选
    }
    ↓
后端 (FastAPI)
    ├─ http/router.py         [HTTP 层]
    ├─ service.py             [业务逻辑: DB + Agent 编排]
    ├─ agent.py               [LLM 翻译]
    └─ llm_providers/         [LLM 抽象层]
    ↓
数据库 (SQLite)
    └─ 存储翻译结果 + token 使用统计
    ↓
前端接收:
    {
      "entry_id": "article-123",
      "target_lang": "英文",
      "translation_html": "翻译内容...",
      "status": "success",
      "provider": "openai",
      "model": "gpt-4"
    }
```

## 模块结构

```
agent_translation/
├── AGENT.md                 # 本文件
├── __init__.py              # 公共 API 导出
├── router.py                # 路由分发器（导入自 http/）
├── http/
│   ├── __init__.py
│   └── router.py            # HTTP 端点 + 错误处理
├── service.py               # 应用服务（编排）
└── agent.py                 # 翻译 agent（核心逻辑）
```

## 职责说明

### agent.py — TranslationAgent
**单一职责**: 执行基于 LLM 的翻译

- 接收: 内容（纯文本）、目标语言、LLM 提供者
- 功能: 格式化提示词，通过 `provider.chat()` 调用 LLM，提取响应
- 返回: 翻译文本 + 元数据（提供者、模型、token 使用）
- 不处理: 数据库、HTTP、错误（异常直接冒泡）
- 依赖: 仅 `llm_providers`

### service.py — TranslationService
**单一职责**: 编排翻译工作流

- 接收: HTTP 请求（entry_id、target_lang、provider、model）
- 功能:
  1. 从数据库加载文章（`db.get_article()`）
  2. 解析内容优先级（清洁 markdown → 纯文本 → 原始 HTML）
  3. 获取 LLM 提供者（未指定时使用默认）
  4. 调用 `TranslationAgent`
  5. 优雅处理错误（返回 FAILURE 状态，永不抛异常到 HTTP）
  6. 记录 token 使用（`db.record_usage()`）
  7. 持久化结果（`db.save_agent_result()`）
- 返回: `TranslationResult` 及其状态（SUCCESS 或 FAILURE）
- 依赖: `db`、`llm_providers`、`.agent`

### http/router.py — HTTP 端点
**单一职责**: HTTP 接口

- 端点: `POST /agents/translation`
- 接收: `TranslationRequest` (JSON)
- 功能:
  1. 创建 `TranslationService` 实例
  2. 调用 `service.generate(request)`
  3. 捕获域异常（ArticleNotFoundError、ArticleContentUnavailableError）
  4. 转换为 HTTP 状态码（404、409）
  5. 返回 `TranslationResult` 为 JSON
- 返回: 200 OK（包含 SUCCESS/FAILURE 状态）或 4xx 错误
- 依赖: `.service`、`fastapi`

## 契约（Python）

### 公共 API

```python
# HTTP 层的主入口
from agent_translation import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)  # 挂载 POST /agents/translation
```

### 直接使用（后端到后端）

```python
from agent_translation import TranslationService
from app.schemas.agent import TranslationRequest

service = TranslationService()
request = TranslationRequest(
    entry_id="article-123",
    target_lang="中文",
    provider="openai",      # 可选
    model="gpt-4"           # 可选
)
result = await service.generate(request)
# result.translation_html 包含翻译内容
# result.status 指示成功/失败
```

## 契约（HTTP）

### 端点

```
POST /agents/translation
Content-Type: application/json
```

### 请求格式

```json
{
  "entry_id": "article-123",
  "target_lang": "英文",
  "provider": "openai",
  "model": "gpt-4"
}
```

### 响应格式（成功）

```json
HTTP 200 OK

{
  "entry_id": "article-123",
  "target_lang": "英文",
  "translation_html": "翻译内容在这里...",
  "status": "success",
  "provider": "openai",
  "model": "gpt-4"
}
```

### 响应格式（翻译失败）

```json
HTTP 200 OK

{
  "entry_id": "article-123",
  "target_lang": "英文",
  "translation_html": "",
  "status": "failure",
  "provider": "openai",
  "model": "gpt-4"
}
```

### 错误响应

| 状态码 | 原因 |
|--------|------|
| 404 | 文章（entry_id）不存在 |
| 409 | 文章存在但无内容可翻译 |

## 错误处理哲学

错误处理优雅 — 翻译失败返回 `status: "failure"` 而不是 HTTP 异常：

- **域错误（4xx）**: 文章缺失、无内容 → HTTP 404/409
- **LLM 错误（提供者错误）**: 网络、认证、限流 → HTTP 200 + status: failure
- **意外错误**: 记录日志、记录为失败、返回 `status: failure`

这确保前端始终收到 200 响应，状态字段指示结果。

## 数据流

### 1. 请求到达路由

```python
POST /agents/translation
{
  "entry_id": "article-123",
  "target_lang": "英文",
  "provider": "openai",
  "model": "gpt-4"
}
```

### 2. 服务加载文章

```python
article = get_article("article-123")
if article is None:
    raise ArticleNotFoundError(entry_id)
```

### 3. 服务解析内容

优先级顺序（好 → 差）：
1. **清洁 markdown**（`article_content.cleaned_markdown`）
2. **纯文本**（`article_content.plain_text`）
3. **清洁原始 HTML**（回退）

### 4. 服务获取 LLM 提供者

```python
provider = get_provider(name="openai")  # 无则使用默认
```

### 5. TranslationAgent 执行

```python
agent = TranslationAgent(provider=provider)
result = await agent.translate(
    content="文章文本...",
    target_lang="英文",
    temperature=0.3
)
# 返回: {
#   "translated_text": "...",
#   "provider": "openai",
#   "model": "gpt-4",
#   "usage": {"prompt_tokens": 150, "completion_tokens": 200}
# }
```

### 6. 服务记录使用并保存结果

```python
record_usage(entry_id, "translation", 150, 200, "openai", "gpt-4")
save_agent_result(TranslationResult(...))
```

### 7. 响应返回前端

## 依赖

### 内部
- `app.config` — 数据库路径和设置
- `app.schemas` — 请求/响应类型
- `db` — 数据持久化（读文章、写结果 + 使用）

### 外部
- `llm_providers` — LLM 抽象（OpenAI、Anthropic、Ollama）
- `fastapi` — HTTP 框架（仅路由）

### 不导入
- ❌ `feed_engine` — 职责分离
- ❌ `content_cleaner` — 已应用于存储内容
- ❌ `agent_summary` — 独立模块
- ❌ FastAPI 应用直接引用 — 模块保持库样式

## 配置

### LLM 提供者设置

提供者配置在 `~/.mercury/providers.json`：

```json
{
  "providers": [
    {
      "name": "openai",
      "kind": "openai_compatible",
      "model": "gpt-4",
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-...",
      "is_default": true
    }
  ]
}
```

详见 `llm_providers/AGENT.md` 获取完整配置。

### 翻译请求示例

使用默认提供者：
```python
TranslationRequest(
    entry_id="article-123",
    target_lang="英文"
)
```

指定提供者和模型：
```python
TranslationRequest(
    entry_id="article-123",
    target_lang="英文",
    provider="openai",
    model="gpt-4-turbo"
)
```

## 设计原则

### 1. 低耦合
- `agent.py` → 仅 `llm_providers`
- `service.py` → `db`、`llm_providers`、`.agent`
- `http/router.py` → `.service`、`fastapi`
- 无循环依赖

### 2. 职责清晰
- Agent: 仅 LLM 翻译逻辑
- Service: 编排 + 错误处理
- Router: HTTP 序列化 + 状态码

### 3. 错误处理作为状态
- 失败是**可观察状态**（status: failure），而非异常
- 异常仅对域错误（缺失文章）冒泡
- LLM 错误被捕获并记录为失败

### 4. 内容优先级
始终优先清洁内容：
```
cleaned_markdown > plain_text > stripped_raw_html
```

### 5. 数据库集成
- 读: `get_article()`、`get_article_content()`
- 写: `save_agent_result()`、`record_usage()`
- 永不直接写 SQL

## 测试

### 单元测试

放在 `agent_translation/tests/`：

**test_agent.py**
```python
import pytest
from unittest.mock import AsyncMock
from agent_translation import TranslationAgent
from llm_providers import ChatCompletion, TokenUsage

@pytest.mark.asyncio
async def test_translate_calls_provider():
    mock_provider = AsyncMock()
    mock_provider.name = "openai"
    mock_provider.model = "gpt-4"
    mock_provider.chat.return_value = ChatCompletion(
        content="翻译文本",
        model="gpt-4",
        usage=TokenUsage(prompt_tokens=100, completion_tokens=50)
    )

    agent = TranslationAgent(provider=mock_provider)
    result = await agent.translate("英文文本", "中文")

    assert result["translated_text"] == "翻译文本"
    assert result["provider"] == "openai"
```

**test_service.py**
```python
@pytest.mark.asyncio
async def test_service_loads_article_and_translates():
    # Mock db 函数
    # Mock TranslationAgent
    # 测试完整工作流
```

**test_router.py**
```python
def test_translate_endpoint_returns_200():
    # 使用 FastAPI TestClient
    # Mock service
    # 验证端点行为
```

### 集成测试

放在顶级 `tests/`：

```bash
uv run pytest agent_translation/tests/
uv run pytest tests/test_translation_integration.py
```

## 未来增强

### 1. 双语模式
将源文本与翻译并排展示：
```json
{
  "entry_id": "article-123",
  "target_lang": "英文",
  "bilingual_mode": true,
  "translation_html": "<div class='bilingual'><div class='source'>...</div><div class='translation'>...</div></div>"
}
```

### 2. 缓存
调用 LLM 前检查翻译是否存在：
```python
cached = db.get_latest_agent_result(entry_id, "translation")
if cached and cached.target_lang == request.target_lang:
    return cached  # 跳过 LLM 调用
```

### 3. 语言检测
自动检测源语言，若匹配目标语言则跳过：
```python
from langdetect import detect

source_lang = detect(content)
if source_lang == target_lang_code:
    return TranslationResult(..., translation_html=content, status="skipped")
```

### 4. 流式响应
返回 SSE 用于渐进式翻译显示：
```python
@router.post("/stream")
async def translate_stream(request: TranslationRequest):
    async for chunk in provider.chat(..., stream=True):
        yield f"data: {chunk}\n\n"
```

### 5. 提示词版本化
支持不同领域的不同翻译提示词：
```python
PROMPTS = {
    "technical": "你是技术翻译...",
    "literary": "你是文学翻译...",
    "default": "你是专业翻译..."
}
```

## 验收标准（MVP）

✅ `TranslationAgent` 正确调用 `llm_providers`
✅ `TranslationService` 编排 DB → Agent → DB 流程
✅ HTTP 端点返回 200（包含状态）或 4xx（包含详情）
✅ Token 使用记录到数据库
✅ 失败优雅处理（status: failure，非异常）
✅ 低耦合（清晰的模块边界）
✅ 清晰的缺失文章/内容错误消息
✅ 适用于任何配置的 LLM 提供者

## 参考资料

- `app/schemas/agent.py` — TranslationRequest、TranslationResult
- `app/schemas/entry.py` — 翻译字段
- `llm_providers/AGENT.md` — LLM 提供者抽象
- `llm_providers/__init__.py` — 公共 API
- `db/__init__.py` — 数据库 API
- `backend/AGENT.md` — 整体后端架构
