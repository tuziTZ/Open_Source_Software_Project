from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_summary.service import SummaryService
from app.config import settings
from app.main import app
from app.schemas.agent import SummaryResult, TranslationResult
from app.schemas.entry import Entry
from app.schemas.feed import Feed
from app.schemas.tag import Tag
from db import (
    finish_agent_run,
    init_db,
    save_agent_result,
    save_article,
    save_article_content,
    save_feed,
    save_tag,
    start_agent_run,
    set_article_tags,
)


@pytest.fixture
def qa_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "mercury-qa.db"
    monkeypatch.setattr(settings, "db_path", db_path)
    init_db(db_path)
    return db_path


@pytest.fixture
def qa_client(qa_db: Path) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def test_clean_summary_and_entry_flow_uses_cleaned_content(
    qa_db: Path,
    qa_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_summary.http import router as summary_router

    _seed_article(
        qa_db,
        article_id="article-flow",
        reader_html="""
        <article>
          <h1>Mercury Update</h1>
          <p>Cleaner pipeline prepared this text.</p>
          <p><a href="/deep-dive">Read more</a></p>
        </article>
        """,
    )

    clean_response = qa_client.get("/content/entries/article-flow/clean")

    assert clean_response.status_code == 200
    cleaned_payload = clean_response.json()
    assert 'href="https://example.com/deep-dive"' in cleaned_payload["cleaned_html"]
    assert "# Mercury Update" in cleaned_payload["cleaned_markdown"]

    class FakeAgent:
        async def summarize(self, entry_id: str, content: str) -> dict[str, str]:
            assert entry_id == "article-flow"
            assert "# Mercury Update" in content
            assert "Cleaner pipeline prepared this text." in content
            assert "https://example.com/deep-dive" in content
            assert "<article>" not in content
            return {
                "entry_id": entry_id,
                "summary_text": "Cross-module summary stored",
                "status": "success",
                "provider": "mock",
                "model": "mock-summary",
            }

    monkeypatch.setattr(
        summary_router,
        "get_summary_service",
        lambda: SummaryService(agent_factory=FakeAgent),
    )

    summary_response = qa_client.post(
        "/agents/summary/generate",
        json={"entry_id": "article-flow"},
    )
    detail_response = qa_client.get("/entries/article-flow")
    search_response = qa_client.get("/entries", params={"keyword": "prepared"})

    assert summary_response.status_code == 200
    assert summary_response.json()["summary_text"] == "Cross-module summary stored"

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["reader_html"] == cleaned_payload["cleaned_html"]
    assert detail_payload["summary_text"] == "Cross-module summary stored"

    assert search_response.status_code == 200
    assert [entry["id"] for entry in search_response.json()] == ["article-flow"]


def test_entries_detail_keeps_latest_successful_translation_projection(
    qa_db: Path,
    qa_client: TestClient,
) -> None:
    _seed_article(qa_db, article_id="article-translation", reader_html="<p>Hello Mercury</p>")

    save_agent_result(
        TranslationResult(
            entry_id="article-translation",
            target_lang="zh-CN",
            translation_html="<p>Translated Mercury</p>",
            status="success",
            provider="mock",
            model="mock-translation",
        ),
        qa_db,
    )

    failed_run = start_agent_run(
        article_id="article-translation",
        agent_type="translation",
        provider="mock",
        model="mock-translation",
        target_lang="zh-CN",
        db_path=qa_db,
    )
    finish_agent_run(
        failed_run,
        status="failure",
        output_text="<p>broken</p>",
        error_message="timeout",
        db_path=qa_db,
    )

    detail_response = qa_client.get("/entries/article-translation")
    list_response = qa_client.get("/entries", params={"feed_id": "feed-qa"})

    assert detail_response.status_code == 200
    assert detail_response.json()["translation_html"] == "<p>Translated Mercury</p>"
    assert detail_response.json()["translation_status"] == "success"

    assert list_response.status_code == 200
    assert list_response.json()[0]["translation_html"] == "<p>Translated Mercury</p>"
    assert list_response.json()[0]["translation_status"] == "success"


def test_summary_generation_falls_back_to_plain_text_when_markdown_is_empty(
    qa_db: Path,
    qa_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_summary.http import router as summary_router

    _seed_article(
        qa_db,
        article_id="article-plain-text",
        reader_html="<p>Reader HTML should not be used first.</p>",
    )
    save_article_content(
        article_id="article-plain-text",
        raw_html="<article><p>Stored raw HTML</p></article>",
        cleaned_html="<p>Stored cleaned HTML</p>",
        cleaned_markdown="",
        plain_text="Cleaner plain text fallback",
        content_hash="plain-text-fallback",
        db_path=qa_db,
    )

    class FakeAgent:
        async def summarize(self, entry_id: str, content: str) -> dict[str, str]:
            assert entry_id == "article-plain-text"
            assert content == "Cleaner plain text fallback"
            return {
                "entry_id": entry_id,
                "summary_text": "Plain text fallback summary",
                "status": "success",
                "provider": "mock",
                "model": "mock-summary",
            }

    monkeypatch.setattr(
        summary_router,
        "get_summary_service",
        lambda: SummaryService(agent_factory=FakeAgent),
    )

    response = qa_client.post(
        "/agents/summary/generate",
        json={"entry_id": "article-plain-text"},
    )
    detail_response = qa_client.get("/entries/article-plain-text")

    assert response.status_code == 200
    assert response.json()["summary_text"] == "Plain text fallback summary"
    assert detail_response.status_code == 200
    assert detail_response.json()["summary_text"] == "Plain text fallback summary"


def test_summary_generation_falls_back_to_reader_html_when_cleaned_content_is_blank(
    qa_db: Path,
    qa_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_summary.http import router as summary_router

    _seed_article(
        qa_db,
        article_id="article-reader-fallback",
        reader_html="""
        <article>
          <h1>Reader fallback</h1>
          <p>Used when cleaner data is absent.</p>
        </article>
        """,
    )

    class FakeAgent:
        async def summarize(self, entry_id: str, content: str) -> dict[str, str]:
            assert entry_id == "article-reader-fallback"
            assert content == "Reader fallback Used when cleaner data is absent."
            return {
                "entry_id": entry_id,
                "summary_text": "Reader HTML fallback summary",
                "status": "success",
                "provider": "mock",
                "model": "mock-summary",
            }

    monkeypatch.setattr(
        summary_router,
        "get_summary_service",
        lambda: SummaryService(agent_factory=FakeAgent),
    )

    response = qa_client.post(
        "/agents/summary/generate",
        json={"entry_id": "article-reader-fallback"},
    )

    assert response.status_code == 200
    assert response.json()["summary_text"] == "Reader HTML fallback summary"


def test_recleaning_article_refreshes_entry_projection_and_search_index(
    qa_db: Path,
    qa_client: TestClient,
) -> None:
    _seed_article(
        qa_db,
        article_id="article-refresh",
        reader_html="<p>Original reader HTML</p>",
    )
    save_article_content(
        article_id="article-refresh",
        raw_html="""
        <article>
          <h1>Fresh content</h1>
          <p>Brand new searchable text.</p>
          <a href="/fresh">Fresh link</a>
          <img src="https://tracker.example.com/pixel.gif" width="1" height="1">
        </article>
        """,
        cleaned_html="<p>stale projection</p>",
        cleaned_markdown="stale projection",
        plain_text="stale keyword",
        content_hash="stale-projection",
        db_path=qa_db,
    )

    stale_before = qa_client.get("/entries", params={"keyword": "stale"})
    clean_response = qa_client.get("/content/entries/article-refresh/clean")
    detail_response = qa_client.get("/entries/article-refresh")
    fresh_search = qa_client.get("/entries", params={"keyword": "searchable"})
    stale_after = qa_client.get("/entries", params={"keyword": "stale"})

    assert stale_before.status_code == 200
    assert [entry["id"] for entry in stale_before.json()] == ["article-refresh"]

    assert clean_response.status_code == 200
    assert "pixel.gif" not in clean_response.json()["cleaned_html"]
    assert 'href="https://example.com/fresh"' in clean_response.json()["cleaned_html"]

    assert detail_response.status_code == 200
    assert detail_response.json()["reader_html"] == clean_response.json()["cleaned_html"]

    assert fresh_search.status_code == 200
    assert [entry["id"] for entry in fresh_search.json()] == ["article-refresh"]

    assert stale_after.status_code == 200
    assert stale_after.json() == []


def test_failed_summary_generation_does_not_replace_previous_successful_summary(
    qa_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_summary.http import router as summary_router

    _seed_article(
        qa_db,
        article_id="article-summary-history",
        reader_html="<p>Summary history article</p>",
    )
    save_agent_result(
        SummaryResult(
            entry_id="article-summary-history",
            summary_text="Existing successful summary",
            status="success",
            provider="mock",
            model="mock-summary",
        ),
        qa_db,
    )

    class FailingAgent:
        async def summarize(self, entry_id: str, content: str) -> dict[str, str]:
            raise RuntimeError("summary provider unavailable")

    monkeypatch.setattr(
        summary_router,
        "get_summary_service",
        lambda: SummaryService(agent_factory=FailingAgent),
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/agents/summary/generate",
            json={"entry_id": "article-summary-history"},
        )
        detail_response = client.get("/entries/article-summary-history")

    assert response.status_code == 500
    assert detail_response.status_code == 200
    assert detail_response.json()["summary_text"] == "Existing successful summary"


def test_article_lifecycle_flow_updates_entry_and_aggregate_views(
    qa_db: Path,
    qa_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_summary.http import router as summary_router

    _seed_article(
        qa_db,
        article_id="article-lifecycle",
        reader_html="""
        <article>
          <h1>Lifecycle title</h1>
          <p>Workflow text for the full QA scenario.</p>
        </article>
        """,
    )
    save_tag(
        Tag(id="tag-workflow", name="Workflow", aliases=["qa-flow"], usage_count=0, unread_count=0),
        qa_db,
    )
    set_article_tags("article-lifecycle", ["tag-workflow"], qa_db)

    class FakeAgent:
        async def summarize(self, entry_id: str, content: str) -> dict[str, str]:
            assert entry_id == "article-lifecycle"
            assert "Workflow text for the full QA scenario." in content
            return {
                "entry_id": entry_id,
                "summary_text": "Lifecycle summary stored",
                "status": "success",
                "provider": "mock",
                "model": "mock-summary",
            }

    monkeypatch.setattr(
        summary_router,
        "get_summary_service",
        lambda: SummaryService(agent_factory=FakeAgent),
    )

    initial_feeds = qa_client.get("/feeds")
    initial_tags = qa_client.get("/tags")
    clean_response = qa_client.get("/content/entries/article-lifecycle/clean")
    summary_response = qa_client.post(
        "/agents/summary/generate",
        json={"entry_id": "article-lifecycle"},
    )
    save_agent_result(
        TranslationResult(
            entry_id="article-lifecycle",
            target_lang="zh-CN",
            translation_html="<p>Lifecycle translation</p>",
            status="success",
            provider="mock",
            model="mock-translation",
        ),
        qa_db,
    )
    mark_starred = qa_client.patch("/entries/article-lifecycle/star", json={"is_starred": True})
    mark_read = qa_client.patch("/entries/article-lifecycle/read", json={"is_read": True})
    detail_response = qa_client.get("/entries/article-lifecycle")
    filtered_entries = qa_client.get(
        "/entries",
        params={"feed_id": "feed-qa", "keyword": "Workflow"},
    )
    filtered_tags = qa_client.get("/tags", params={"keyword": "qa-flow"})
    final_feeds = qa_client.get("/feeds", params={"keyword": "QA"})
    final_tags = qa_client.get("/tags")

    assert initial_feeds.status_code == 200
    assert initial_feeds.json()[0]["unread_count"] == 1
    assert initial_tags.status_code == 200
    assert initial_tags.json()[0]["unread_count"] == 1

    assert clean_response.status_code == 200
    assert summary_response.status_code == 200
    assert summary_response.json()["summary_text"] == "Lifecycle summary stored"

    assert mark_starred.status_code == 200
    assert mark_starred.json()["is_starred"] is True
    assert mark_read.status_code == 200
    assert mark_read.json()["is_read"] is True

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["summary_text"] == "Lifecycle summary stored"
    assert detail_payload["translation_html"] == "<p>Lifecycle translation</p>"
    assert detail_payload["translation_status"] == "success"
    assert detail_payload["is_starred"] is True
    assert detail_payload["is_read"] is True
    assert detail_payload["tag_ids"] == ["tag-workflow"]

    assert filtered_entries.status_code == 200
    assert [entry["id"] for entry in filtered_entries.json()] == ["article-lifecycle"]
    assert filtered_tags.status_code == 200
    assert filtered_tags.json()[0]["id"] == "tag-workflow"

    assert final_feeds.status_code == 200
    assert final_feeds.json()[0]["unread_count"] == 0
    assert final_tags.status_code == 200
    assert final_tags.json()[0]["usage_count"] == 1
    assert final_tags.json()[0]["unread_count"] == 0


def test_deleting_article_removes_detail_search_and_aggregate_presence(
    qa_db: Path,
    qa_client: TestClient,
) -> None:
    _seed_article(
        qa_db,
        article_id="article-delete",
        reader_html="<p>Delete me from every projection.</p>",
    )
    save_tag(
        Tag(id="tag-delete", name="Delete", aliases=["cleanup"], usage_count=0, unread_count=0),
        qa_db,
    )
    set_article_tags("article-delete", ["tag-delete"], qa_db)
    save_article_content(
        article_id="article-delete",
        raw_html="<article><p>Delete me from every projection.</p></article>",
        cleaned_html="<p>Delete me from every projection.</p>",
        cleaned_markdown="Delete me from every projection.",
        plain_text="Delete me from every projection.",
        content_hash="delete-everywhere",
        db_path=qa_db,
    )

    detail_before = qa_client.get("/entries/article-delete")
    search_before = qa_client.get("/entries", params={"keyword": "projection"})
    tags_before = qa_client.get("/tags")
    feeds_before = qa_client.get("/feeds")
    delete_response = qa_client.delete("/entries/article-delete")
    detail_after = qa_client.get("/entries/article-delete")
    search_after = qa_client.get("/entries", params={"keyword": "projection"})
    tags_after = qa_client.get("/tags", params={"keyword": "cleanup"})
    feeds_after = qa_client.get("/feeds")

    assert detail_before.status_code == 200
    assert search_before.status_code == 200
    assert [entry["id"] for entry in search_before.json()] == ["article-delete"]
    assert tags_before.status_code == 200
    assert tags_before.json()[0]["usage_count"] == 1
    assert tags_before.json()[0]["unread_count"] == 1
    assert feeds_before.status_code == 200
    assert feeds_before.json()[0]["unread_count"] == 1

    assert delete_response.status_code == 200
    assert delete_response.json() == {"entry_id": "article-delete", "deleted": True}

    assert detail_after.status_code == 404
    assert search_after.status_code == 200
    assert search_after.json() == []
    assert tags_after.status_code == 200
    assert tags_after.json()[0]["usage_count"] == 0
    assert tags_after.json()[0]["unread_count"] == 0
    assert feeds_after.status_code == 200
    assert feeds_after.json()[0]["unread_count"] == 0


def _seed_article(
    db_path: Path,
    article_id: str,
    reader_html: str,
    *,
    feed_id: str = "feed-qa",
    feed_title: str = "QA Feed",
    url: str = "https://example.com/posts/1",
) -> None:
    save_feed(
        Feed(
            id=feed_id,
            title=feed_title,
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
            unread_count=0,
            status="idle",
        ),
        db_path,
    )
    save_article(
        Entry(
            id=article_id,
            feed_id=feed_id,
            title=f"{article_id} title",
            summary="Cross-module regression coverage",
            author="QA Team",
            url=url,
            published_at="2026-06-01T08:00:00Z",
            is_read=False,
            is_starred=False,
            tag_ids=[],
            reader_html=reader_html,
            web_preview="",
            related_entry_ids=[],
            note="",
            summary_text="",
            translation_html=None,
            translation_status="idle",
        ),
        db_path,
    )
