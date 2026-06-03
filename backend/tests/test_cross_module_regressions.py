from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_summary.service import SummaryService
from app.config import settings
from app.main import app
from app.schemas.agent import TranslationResult
from app.schemas.entry import Entry
from app.schemas.feed import Feed
from db import (
    finish_agent_run,
    init_db,
    save_agent_result,
    save_article,
    save_feed,
    start_agent_run,
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


def _seed_article(db_path: Path, article_id: str, reader_html: str) -> None:
    save_feed(
        Feed(
            id="feed-qa",
            title="QA Feed",
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
            feed_id="feed-qa",
            title=f"{article_id} title",
            summary="Cross-module regression coverage",
            author="QA Team",
            url="https://example.com/posts/1",
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
