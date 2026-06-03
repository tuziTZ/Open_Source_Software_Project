from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.schemas.feed import Feed
from feed_engine.fetcher import FetchResponse
from feed_engine.opml import export_opml, parse_opml
from feed_engine.parser import parse_feed_root, parse_xml
from feed_engine.service import sync_feed
from feed_engine.validation import validate_feed_xml

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_parse_rss20_fixture() -> None:
    root = parse_xml(fixture("rss20_basic.xml"))
    parsed = parse_feed_root(root, "https://example.com/rss.xml")

    assert parsed.format == "rss2"
    assert parsed.title == "Mercury Blog"
    assert parsed.site_url == "https://example.com"
    assert len(parsed.entries) == 1
    assert parsed.entries[0].title == "First Article"
    assert parsed.entries[0].published_at == "2026-05-25T10:00:00Z"


def test_parse_atom_fixture() -> None:
    root = parse_xml(fixture("atom_basic.xml"))
    parsed = parse_feed_root(root, "https://example.com/atom.xml")

    assert parsed.format == "atom"
    assert parsed.title == "Mercury Atom"
    assert parsed.site_url == "https://example.com"
    assert len(parsed.entries) == 1
    assert parsed.entries[0].author == "Atom Author"


def test_validate_rejects_unknown_xml() -> None:
    result = validate_feed_xml(b"<not-feed />")

    assert result.valid is False
    assert result.format == "unknown"
    assert result.errors[0].code == "UNSUPPORTED_FEED"


def test_parse_nested_opml() -> None:
    feeds, errors = parse_opml(fixture("opml_nested.xml"))

    assert errors == []
    assert [feed.title for feed in feeds] == ["Mercury Blog", "Atom Feed"]


def test_export_opml_escapes_feed_values() -> None:
    payload = export_opml(
        [
            Feed(
                id="feed-1",
                title="A & B",
                site_url="https://example.com?a=1&b=2",
                feed_url="https://example.com/rss.xml",
                unread_count=0,
                status="success",
            )
        ]
    )

    assert '<opml version="2.0">' in payload
    assert 'text="A &amp; B"' in payload
    assert "https://example.com?a=1&amp;b=2" in payload


def test_sync_feed_uses_storage_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    import db
    import feed_engine.service as service

    saved = []
    metadata = []
    feed = Feed(
        id="feed-001",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/rss.xml",
        unread_count=0,
        status="idle",
    )

    async def fake_fetch_feed(*args, **kwargs):
        return FetchResponse(
            status_code=200,
            final_url="https://example.com/rss.xml",
            body=fixture("rss20_basic.xml"),
            etag="etag-value",
            last_modified="Mon, 25 May 2026 12:00:00 GMT",
            content_type="application/rss+xml",
        )

    monkeypatch.setattr(
        db,
        "get_feed",
        lambda feed_id: feed if feed_id == "feed-001" else None,
        raising=False,
    )
    monkeypatch.setattr(db, "save_articles", lambda articles: saved.extend(articles), raising=False)
    monkeypatch.setattr(
        db,
        "get_feed_sync_metadata",
        lambda feed_id: {"etag": None, "last_modified": None} if feed_id == "feed-001" else None,
        raising=False,
    )
    monkeypatch.setattr(
        db,
        "update_feed_sync_metadata",
        lambda **kwargs: metadata.append(kwargs),
        raising=False,
    )
    monkeypatch.setattr(service, "fetch_feed", fake_fetch_feed)

    result = asyncio.run(sync_feed("feed-001"))

    assert result.status == "success"
    assert result.fetched == 1
    assert result.saved == 1
    assert saved[0].feed_id == "feed-001"
    assert saved[0].title == "First Article"
    assert metadata[0]["etag"] == "etag-value"
