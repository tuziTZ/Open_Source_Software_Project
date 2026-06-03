# backend/db Agent Guide

Owner: Storage Engineer

本文件是 Mercury 数据库层的强约束文档。组员和 Coding Agent 修改 `backend/db/` 前必须先读本文件。

目标不是只把一次改动做完，而是把发现的问题沉淀成可执行的技术规范，让后续人和 AI 都按同一套规则工作。

## Mission

`backend/db/` 提供 Mercury 的本地 SQLite 持久化能力：

- Feed / Article / Article Content 存储
- Tag / Article Tag 存储
- Agent Run / Agent Step / Agent Result 存储
- Provider Settings / App Config 存储
- Usage 统计
- Article Search
- Migration 管理
- 数据库备份和测试支持

这是一个 library，不是 HTTP 模块。

前端不能直接访问 `backend/db/`。HTTP route、Feed Engine、Content Cleaner、Agent 模块通过 `db` 包导出的 repository API 调用数据库。

## Hard Rules

### 1. Do Not Write SQL Outside backend/db

禁止在以下目录中直接 `sqlite3.connect()` 或手写 SQL：

- `backend/feed_engine/`
- `backend/content_cleaner/`
- `backend/agent_summary/`
- `backend/agent_translation/`
- `backend/llm_providers/`
- `backend/app/routers/`

其他模块必须通过 `from db import ...` 调用公开 API。

原因：

- schema、migration、WAL、foreign key、事务和跨平台路径必须统一管理。
- 其他模块散写 SQL 会导致数据库结构和行为失控。
- 表结构变化时，应优先保持 repository API 稳定。

### 2. backend/db Must Stay at the Bottom of the Dependency Graph

`backend/db` 可以 import：

- Python stdlib
- `app.schemas`
- `app.config`
- `db.*`

`backend/db` 不允许 import：

- `feed_engine`
- `content_cleaner`
- `agent_summary`
- `agent_translation`
- `llm_providers`
- FastAPI routers

数据库层只做存储，不承载上层业务编排。

### 3. Public API Only Through db.__init__

对其他模块稳定暴露的接口必须从 `backend/db/__init__.py` 导出。

推荐调用：

```py
from db import save_feed, save_article, get_article
```

不推荐跨文件深 import：

```py
from db.repositories.article_repo import save_article
```

除非是在 `backend/db` 内部测试私有行为。

## Search Rules

老板明确提出：数据库层需要支持搜索 level 的设计，而不是只有一个模糊 `search()`。

Mercury 当前搜索分为三层：

### Level 1: Metadata Search

搜索轻量字段，例如：

- feed title
- feed url
- article title
- article summary

适用场景：

- Feed 列表过滤
- 文章标题关键词搜索
- UI 快速筛选

实现方式：

- `query_feeds(keyword=...)`
- `search_articles(keyword=...)`

### Level 2: SQLite Full Text Search

搜索文章正文、摘要、标题。

当前使用 SQLite FTS5：

- `article_search` 是普通投影表
- `article_fts` 是 FTS5 virtual table
- triggers 负责同步 `article_search -> article_fts`

约束：

- 搜索 API 仍然是 `search_articles()`，不要让上层直接操作 FTS 表。
- 更新文章标题/摘要时必须同步 `article_search`。
- 更新 cleaned plain text 时必须同步 `article_search`。
- 测试必须覆盖搜索投影更新后旧关键词失效、新关键词生效。

### Level 3: RAG / Embedding Search

RAG、embedding、向量数据库属于未来增强，不属于当前 SQLite 基础存储的默认依赖。

当前约束：

- 不要为了 RAG 引入大型第三方数据库依赖。
- 不要在 `backend/db` 中直接绑定某个 LLM Provider 或 embedding provider。
- 如果未来需要 RAG，应通过新增独立模块或可选 adapter 实现，并用 migration 增加必要元数据表。

推荐未来结构：

```text
backend/rag_index/
  service.py
  embeddings.py
  index_repo.py
```

`backend/db` 可以提供文章内容和 metadata，RAG 模块负责索引和召回。

## Migration Rules

老板明确提出：数据库 metadata 结构会变化，版本演进必须可控。

### 1. Never Modify Old Migrations After Merge

已合入主分支的 migration 不要回头改。

新增表、字段、索引、trigger、virtual table 时，新增文件：

```text
backend/db/schema/005_<topic>.sql
backend/db/schema/006_<topic>.sql
```

不要直接修改：

```text
001_initial.sql
002_mature_storage.sql
003_agent_status_constraints.sql
004_article_fts.sql
```

除非这些 migration 还没有进入公共分支。

### 2. Migrations Must Be Replayable

必须满足：

- 空数据库可以执行全部 migration。
- 只执行过旧 migration 的数据库可以升级到最新。
- 重复执行 `init_db()` 不报错。
- migration 失败时不能写入 `schema_migrations`。

测试要求：

- `tests/test_db_migrations.py`
- `tests/test_schema_compatibility.py`

### 3. Prefer Additive Changes

优先新增：

- table
- column
- index
- trigger
- virtual table

谨慎执行：

- rename table
- drop column
- rebuild table
- destructive data migration

SQLite 对修改已有约束不友好。需要给旧表新增约束时，优先考虑：

- trigger
- 新增投影表
- 新增校验 repository

例如 `agent_runs.status` 使用 trigger 约束合法状态，而不是重建表。

### 4. Metadata Must Stay Queryable

schema 元数据必须可查：

```sql
SELECT version FROM schema_migrations;
```

不要跳过 `schema_migrations` 记录。

## Dependency and Distribution Rules

老板明确提出：第三方包可能解决 migration 或搜索问题，但应用分发会变麻烦。

Mercury 是跨平台桌面应用，数据库层依赖必须谨慎。

### Allowed by Default

优先使用：

- Python stdlib `sqlite3`
- `pathlib`
- `json`
- `uuid`
- `datetime`
- Pydantic schemas already in app

### Use With Review

以下依赖只有在明确收益大于分发成本时才能引入：

- ORM
- async SQLite wrapper
- migration framework
- search/index library
- native extension package

引入前必须说明：

- 为什么 stdlib sqlite3 不够
- Windows / Linux / macOS 是否都能安装
- 是否影响 Tauri sidecar 打包
- 是否增加 CI 和用户安装成本
- 是否有纯 Python 替代

### Avoid for Storage Core

数据库核心层避免依赖：

- 大型 ORM
- 平台相关 native package
- 外部数据库服务
- LLM provider SDK
- embedding SDK
- 向量数据库 SDK

这些会增加桌面应用分发复杂度。

## Current Module Layout

```text
backend/db/
  __init__.py
  AGENT.md
  README.md
  connection.py
  migrations.py
  errors.py
  maintenance.py
  session.py
  schema/
    001_initial.sql
    002_mature_storage.sql
    003_agent_status_constraints.sql
    004_article_fts.sql
  repositories/
    __init__.py
    feed_repo.py
    article_repo.py
    tag_repo.py
    agent_repo.py
    usage_repo.py
    provider_repo.py
    config_repo.py
```

新增 repository 时必须：

1. 放在 `backend/db/repositories/`。
2. 在 `backend/db/repositories/__init__.py` 导出。
3. 在 `backend/db/__init__.py` 导出。
4. 补测试。
5. 如果影响其他组调用，更新 `backend/db/README.md`。

## Public API Groups

Feed:

```py
save_feed()
save_feeds()
get_feed()
query_feeds()
update_feed_sync_metadata()
get_feed_sync_metadata()
delete_feed()
```

Article:

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

Content:

```py
save_article_content()
get_article_content()
```

## Feed to Cleaner Compatibility

Remote Feed Engine currently maps parsed entry raw HTML into `Entry.reader_html`.

Storage must preserve this integration contract:

- On first `save_article()` / `save_articles()`, seed `article_content.raw_html` from `Entry.reader_html`.
- Do not overwrite existing `article_content.raw_html` during later article metadata updates.
- Do not overwrite existing cleaned content during later article metadata updates.
- Cleaner owns later writes to `cleaned_html`, `cleaned_markdown`, `plain_text`, and `content_hash` through `save_article_content()`.

This keeps the real chain working:

```text
Feed Engine parsed raw_html
  -> Entry.reader_html
  -> save_articles()
  -> article_content.raw_html
  -> Cleaner get_article_content()
  -> Cleaner save_article_content()
```

Feed sync metadata is not part of the public `Feed` schema. Feed Engine should read HTTP cache metadata through:

```py
get_feed_sync_metadata(feed_id)
```

Do not add `etag` / `last_modified` to `Feed` without coordinating OpenAPI and frontend type changes.

Tag:

```py
save_tag()
set_article_tags()
```

Agent:

```py
start_agent_run()
append_agent_step()
finish_agent_run()
save_agent_result()
get_latest_agent_result()
```

Provider / Config / Usage:

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

Maintenance:

```py
backup_database()
storage_session()
```

## Testing Rules

提交前必须运行：

```bash
uv run ruff check
uv run pytest
```

如果修改了数据库 schema 或 migration，必须至少运行：

```bash
uv run pytest tests/test_db_migrations.py tests/test_schema_compatibility.py -v
```

如果修改了 Feed / Cleaner / Agent 对接，必须至少运行：

```bash
uv run pytest tests/test_storage_integration.py tests/test_storage_edge_cases.py -v
```

如果修改了搜索，必须至少运行：

```bash
uv run pytest tests/test_article_repo.py tests/test_storage_edge_cases.py -v
```

测试数据库必须使用：

- `tmp_path`
- 临时文件数据库

不要写用户真实数据库：

```text
~/.mercury/mercury.db
```

## Coding Agent Trace Rules

使用 Coding Agent 做非平凡改动时，必须写 `.agent-traces/`。

文件名：

```text
.agent-traces/YYYY-MM-DD-<member>-<topic>.md
```

内容必须包含：

- Goal
- Approach
- Decisions
- Surprises
- Follow-ups

不要提交原始对话全文。提交短摘要。

如果 AI 在实现中发现新风险，应把风险沉淀到以下位置之一：

- `backend/db/AGENT.md`
- `backend/db/README.md`
- `docs/storage-engineer-guide.md`
- 测试用例

把“改的过程”变成可执行规范，而不是只留在聊天记录里。

## Acceptance Criteria

数据库层改动可合并前必须满足：

1. `uv run ruff check` 通过。
2. `uv run pytest` 通过。
3. 新 public API 已从 `db.__init__` 导出。
4. 新 schema 改动使用新 migration。
5. migration 可从空库重放。
6. 旧数据库可升级到最新 schema。
7. 其他模块没有直接写 SQL。
8. 搜索改动有投影/FTS 一致性测试。
9. Agent 状态值遵守 `idle | queued | running | success | failure | cancelled`。
10. 如使用 Coding Agent，已新增 `.agent-traces/` 摘要。

## References

- `backend/db/README.md`: 面向组员的 API 使用说明
- `docs/storage-engineer-guide.md`: 存储工程师从 0 到 1 实施指南
- `backend/app/config.py`: 数据库路径配置
- `backend/app/schemas/`: Pydantic model
- `tests/test_storage_integration.py`: Feed / Cleaner / Agent 跨模块存储链路
- `tests/test_schema_compatibility.py`: migration 兼容性测试
