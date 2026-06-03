# Mercury 存储层使用说明

本文档面向 Mercury 后端其他模块成员，说明如何使用 `backend/db/` 提供的 SQLite 存储 API。

如果你是 Feed 工程师、内容清洗工程师、Summary/Translation Agent 工程师、Provider 工程师或 route 层开发者，请优先阅读本文档。

## 基本原则

所有业务模块都应该通过 `db` 包导出的 repository API 访问数据库：

```py
from db import save_feed, save_article, get_article
```

不要在 `backend/db/` 之外直接写 SQL：

```py
# 不推荐：不要在 feed_engine / content_cleaner / agent_* / app routes 里直接这样做
import sqlite3

conn = sqlite3.connect("mercury.db")
conn.execute("SELECT * FROM articles")
```

原因：

- 存储层统一维护 schema、migration、WAL、外键、事务和跨平台路径。
- 其他模块直接写 SQL 容易绕过约束，导致本地数据库结构和数据行为不一致。
- 后续表结构调整时，只要 repository API 稳定，其他模块不需要跟着改 SQL。

## 初始化数据库

应用启动时已经在 FastAPI lifespan 中调用 `init_db()`，一般业务模块不需要手动初始化。

测试或脚本中可以这样初始化临时数据库：

```py
from pathlib import Path

from db import init_db

db_path = Path("mock-test.db")
init_db(db_path)
```

默认数据库路径来自：

```py
settings.resolved_db_path()
```

请不要在业务模块里硬编码 Windows / Linux / macOS 路径。

## Feed 工程师示例

Feed 工程师负责解析 RSS / Atom / OPML，然后把 Feed 和 Article 交给存储层。

```py
from app.schemas.entry import Entry
from app.schemas.feed import Feed
from db import save_feed, save_articles, update_feed_sync_metadata

feed = Feed(
    id="feed-001",
    title="Mercury Blog",
    site_url="https://example.com",
    feed_url="https://example.com/rss.xml",
    unread_count=0,
    status="success",
)

articles = [
    Entry(
        id="article-001",
        feed_id="feed-001",
        title="First Article",
        summary="Parsed from RSS",
        author="Mercury Team",
        url="https://example.com/articles/1",
        published_at="2026-05-25T10:00:00Z",
        is_read=False,
        is_starred=False,
        tag_ids=[],
        reader_html="",
        web_preview="",
        related_entry_ids=[],
        note="",
        summary_text="",
        translation_html=None,
        translation_status="idle",
    )
]

save_feed(feed)
save_articles(articles)

update_feed_sync_metadata(
    feed_id="feed-001",
    last_fetched_at="2026-05-25T12:00:00Z",
    etag="etag-value",
    last_modified="Mon, 25 May 2026 12:00:00 GMT",
    status="success",
)
```

兼容约定：

- Feed Engine 初次保存 `Entry` 时，`Entry.reader_html` 会作为 `article_content.raw_html` 的初始值写入。
- 这让 Cleaner 可以通过 `get_article_content(article_id).raw_html` 读取 Feed 原始 HTML。
- 后续 Cleaner 调用 `save_article_content()` 后，会写入 cleaned HTML / Markdown / plain text。
- 再次 `save_article()` 只更新文章 metadata 和搜索标题/摘要，不会覆盖已存在的 `raw_html` 或 cleaned content。

读取 Feed 同步元数据：

```py
from db import get_feed_sync_metadata

metadata = get_feed_sync_metadata("feed-001")
if metadata is not None:
    etag = metadata["etag"]
    last_modified = metadata["last_modified"]
```

读取 Feed 列表：

```py
from db import get_feed, query_feeds

feed = get_feed("feed-001")
feeds = query_feeds()
matched = query_feeds("Mercury")
```

注意：

- `save_feed()` 和 `save_articles()` 都是 upsert，同一个 ID 重复保存会更新，不会重复插入。
- `save_articles()` 适合一次同步多篇文章，比循环调用 `save_article()` 更适合同步场景。
- Feed 的 `unread_count` 由查询时根据未读文章计算，不需要调用方手动维护。

## Article / 阅读侧示例

读取文章列表：

```py
from db import list_articles

articles = list_articles(feed_id="feed-001", limit=50, offset=0)
```

读取文章详情：

```py
from db import get_article

article = get_article("article-001")
if article is not None:
    print(article.title)
    print(article.reader_html)
```

更新阅读状态：

```py
from db import mark_article_read, mark_article_starred, update_article_note

mark_article_read("article-001", True)
mark_article_starred("article-001", True)
update_article_note("article-001", "这篇文章值得回看")
```

删除文章：

```py
from db import delete_article

delete_article("article-001")
```

删除 Feed：

```py
from db import delete_feed

delete_feed("feed-001")
```

删除 Feed 会通过外键级联删除它下面的文章、正文、Agent 运行记录和文章标签关系。

## Cleaner 工程师示例

内容清洗工程师通常需要：

1. 读取文章原始内容。
2. 清洗 HTML。
3. 生成 Markdown / plain text。
4. 写回清洗结果。

读取正文：

```py
from db import get_article_content

content = get_article_content("article-001")
if content is not None:
    raw_html = content.raw_html
```

写回清洗结果：

```py
from db import save_article_content

save_article_content(
    article_id="article-001",
    raw_html="<main><p>Hello Mercury</p></main>",
    cleaned_html="<p>Hello Mercury</p>",
    cleaned_markdown="Hello Mercury",
    plain_text="Hello Mercury",
    content_hash="hash-001",
)
```

写回后：

- `get_article("article-001").reader_html` 会返回 `cleaned_html`。
- `search_articles()` 可以搜索 `plain_text`。
- `content_hash` 可用于判断文章内容是否变化，避免重复清洗。

## TagAgent 示例

保存标签：

```py
from app.schemas.tag import Tag
from db import save_tag, set_article_tags

save_tag(
    Tag(
        id="tag-ai",
        name="AI",
        aliases=["llm", "large-language-model"],
        usage_count=0,
        unread_count=0,
    )
)

set_article_tags("article-001", ["tag-ai"])
```

按标签筛选文章：

```py
from db import list_articles

ai_articles = list_articles(tag_id="tag-ai")
```

## Agent 示例

Summary / Translation Agent 可以使用两种方式保存结果。

### 方式一：保存最终结果

Summary：

```py
from app.schemas.agent import SummaryResult
from db import save_agent_result

save_agent_result(
    SummaryResult(
        entry_id="article-001",
        summary_text="这是一段摘要。",
        status="success",
        provider="mock",
        model="mock-summary",
    )
)
```

Translation：

```py
from app.schemas.agent import TranslationResult
from db import save_agent_result

save_agent_result(
    TranslationResult(
        entry_id="article-001",
        target_lang="zh-CN",
        translation_html="<p>翻译后的内容</p>",
        status="success",
        provider="mock",
        model="mock-translation",
    )
)
```

读取最新成功结果：

```py
from db import get_latest_agent_result

summary = get_latest_agent_result("article-001", "summary")
translation = get_latest_agent_result(
    "article-001",
    "translation",
    target_lang="zh-CN",
)
```

### 方式二：记录完整 Agent Trace

如果 Agent 有多个步骤，建议记录 run 和 step：

```py
from db import append_agent_step, finish_agent_run, start_agent_run

run_id = start_agent_run(
    article_id="article-001",
    agent_type="summary",
    provider="mock",
    model="mock-summary",
)

append_agent_step(
    run_id,
    name="load_article",
    status="success",
    output_json={"article_id": "article-001"},
)

append_agent_step(
    run_id,
    name="call_llm",
    status="success",
    input_json={"tokens": 1000},
    output_json={"tokens": 200},
)

finish_agent_run(
    run_id,
    status="success",
    output_text="这是一段摘要。",
    prompt_tokens=1000,
    completion_tokens=200,
)
```

Agent 状态值必须使用：

```text
idle
queued
running
success
failure
cancelled
```

不要使用：

```text
done
ok
failed
error
```

数据库会拒绝非法状态值。

## Provider Settings 示例

LLM Provider 配置存储在 `provider_settings` 中。

不要把真实 API key 明文存入 SQLite。只存密钥引用：

```py
from db import get_provider_settings, save_provider_settings

save_provider_settings(
    provider="openai-compatible",
    enabled=True,
    base_url="https://api.example.com/v1",
    default_model="example-model",
    api_key_ref="secret://openai-compatible",
    settings={"temperature": 0.2},
)

settings = get_provider_settings("openai-compatible")
```

删除 Provider 配置：

```py
from db import delete_provider_settings

delete_provider_settings("openai-compatible")
```

## App Config 示例

应用配置使用 JSON 存储：

```py
from db import get_app_config, set_app_config

set_app_config("ui.locale", {"value": "zh-CN"})
locale = get_app_config("ui.locale", default={"value": "en-US"})
```

删除配置：

```py
from db import delete_app_config

delete_app_config("ui.locale")
```

## Usage 示例

记录 LLM 用量：

```py
from db import query_usage, record_usage

record_usage(
    day="2026-05-25",
    provider="mock",
    model="mock-summary",
    agent="summary",
    prompt_tokens=1000,
    completion_tokens=200,
)

buckets = query_usage(
    start_day="2026-05-01",
    end_day="2026-05-31",
    provider="mock",
    agent="summary",
)
```

`query_usage()` 返回 `list[UsageBucket]`。

## Search 示例

搜索文章标题、摘要和清洗后的正文：

```py
from db import search_articles

results = search_articles("Mercury", limit=20)
```

当前搜索优先使用 SQLite FTS5，并保留 LIKE fallback。

## Backup 示例

Local-first 应用建议提供数据库备份能力：

```py
from pathlib import Path

from db import backup_database

backup_database(Path("backup/mercury.db"))
```

如果应用正在运行，优先使用 `backup_database()`，不要直接复制数据库文件。

## 测试示例

单元测试中请使用 `tmp_path`，避免写入真实用户数据库：

```py
from app.schemas.feed import Feed
from db import get_feed, init_db, save_feed


def test_save_and_get_feed(tmp_path):
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    feed = Feed(
        id="feed-001",
        title="Mock Feed",
        site_url="https://example.com",
        feed_url="https://example.com/rss.xml",
        unread_count=0,
        status="idle",
    )

    save_feed(feed, db_path)

    assert get_feed("feed-001", db_path) == feed
```

推荐运行：

```bash
uv run ruff check
uv run pytest
```

只验证存储集成链路：

```bash
uv run pytest tests/test_storage_integration.py -v
```

## 当前主要 API 清单

Feed：

```py
save_feed()
save_feeds()
get_feed()
query_feeds()
update_feed_sync_metadata()
get_feed_sync_metadata()
delete_feed()
```

Article：

```py
save_article()
save_articles()
get_article()
list_articles()
delete_article()
mark_article_read()
mark_article_starred()
update_article_note()
search_articles()
```

Content：

```py
save_article_content()
get_article_content()
```

Tag：

```py
save_tag()
set_article_tags()
```

Agent：

```py
start_agent_run()
append_agent_step()
finish_agent_run()
save_agent_result()
get_latest_agent_result()
```

Provider / Config / Usage：

```py
save_provider_settings()
get_provider_settings()
list_provider_settings()
delete_provider_settings()
set_app_config()
get_app_config()
delete_app_config()
record_usage()
query_usage()
```

Maintenance：

```py
backup_database()
storage_session()
```

## 提交前检查

提交前请至少运行：

```bash
uv run ruff check
uv run pytest
```

如果你改了 Feed / Cleaner / Agent 对接逻辑，建议额外运行：

```bash
uv run pytest tests/test_storage_integration.py tests/test_storage_edge_cases.py -v
```
