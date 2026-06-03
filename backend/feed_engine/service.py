from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.schemas.entry import Entry
from app.schemas.feed import Feed
from feed_engine.errors import FeedEngineError
from feed_engine.fetcher import FetchResponse, fetch_feed
from feed_engine.ids import make_entry_id, make_feed_id
from feed_engine.opml import export_opml as render_opml
from feed_engine.opml import parse_opml
from feed_engine.parser import parse_feed_root, parse_xml
from feed_engine.storage import require_db_function
from feed_engine.types import FetchMetadata, OPMLImportResult, ParsedFeed, SyncResult


async def parse_feed(url: str) -> ParsedFeed:
    parsed, _metadata, _response = await _fetch_and_parse(url)
    return parsed


async def subscribe_feed(url: str, *, sync: bool = True) -> Feed:
    parsed, metadata, response = await _fetch_and_parse(url)
    feed = _feed_from_parsed(parsed)
    save_feed = require_db_function("save_feed")
    save_feed(feed)

    if sync:
        articles = _entries_from_parsed(feed.id, parsed)
        if articles:
            save_articles = require_db_function("save_articles")
            save_articles(articles)
        _update_sync_metadata(feed.id, response, status="success")
    else:
        _update_sync_metadata(feed.id, response, status="idle")

    if metadata.final_url != url and not feed.feed_url:
        feed.feed_url = metadata.final_url
    return feed


def list_feeds(query: str | None = None) -> list[Feed]:
    query_feeds = require_db_function("query_feeds")
    if query:
        return list(query_feeds(query))
    return list(query_feeds())


def delete_feed(feed_id: str) -> dict[str, bool]:
    delete = require_db_function("delete_feed")
    delete(feed_id)
    return {"deleted": True}


async def sync_feed(feed_id: str) -> SyncResult:
    get_feed = require_db_function("get_feed")
    feed = get_feed(feed_id)
    if feed is None:
        raise FeedEngineError(
            "FEED_NOT_FOUND",
            "Feed subscription was not found.",
            status_code=404,
            context={"feed_id": feed_id},
        )

    get_sync_metadata = require_db_function("get_feed_sync_metadata")
    sync_metadata = get_sync_metadata(feed_id) or {}
    etag = sync_metadata.get("etag")
    last_modified = sync_metadata.get("last_modified")
    try:
        response = await fetch_feed(feed.feed_url, etag=etag, last_modified=last_modified)
    except FeedEngineError:
        _update_sync_metadata(feed_id, None, status="failure")
        raise

    if response.status_code == 304:
        _update_sync_metadata(feed_id, response, status="success")
        return SyncResult(
            feed_id=feed_id,
            status="success",
            fetched=0,
            saved=0,
            not_modified=True,
        )

    parsed = _parse_response_body(response)
    articles = _entries_from_parsed(feed_id, parsed)
    save_articles = require_db_function("save_articles")
    save_articles(articles)
    _update_sync_metadata(feed_id, response, status="success")
    return SyncResult(
        feed_id=feed_id,
        status="success",
        fetched=len(parsed.entries),
        saved=len(articles),
    )


async def sync_all_feeds() -> list[SyncResult]:
    results: list[SyncResult] = []
    for feed in list_feeds():
        results.append(await sync_feed(feed.id))
    return results


def import_opml(payload: bytes) -> OPMLImportResult:
    feeds, parse_errors = parse_opml(payload)
    get_feed = require_db_function("get_feed")
    save_feed = require_db_function("save_feed")
    imported: list[Feed] = []
    skipped = 0

    for feed in feeds:
        existing = get_feed(feed.id)
        if existing is not None:
            skipped += 1
            continue
        save_feed(feed)
        imported.append(feed)

    return OPMLImportResult(
        imported=len(imported),
        skipped=skipped,
        errors=parse_errors,
        feeds=imported,
    )


def export_opml() -> str:
    return render_opml(list_feeds())


async def _fetch_and_parse(url: str) -> tuple[ParsedFeed, FetchMetadata, FetchResponse]:
    response = await fetch_feed(url)
    parsed = _parse_response_body(response)
    metadata = FetchMetadata(
        final_url=response.final_url,
        etag=response.etag,
        last_modified=response.last_modified,
    )
    return parsed, metadata, response


def _parse_response_body(response: FetchResponse) -> ParsedFeed:
    root = parse_xml(response.body)
    return parse_feed_root(root, response.final_url)


def _feed_from_parsed(parsed: ParsedFeed) -> Feed:
    return Feed(
        id=make_feed_id(parsed.feed_url),
        title=parsed.title,
        site_url=parsed.site_url,
        feed_url=parsed.feed_url,
        unread_count=0,
        status="success",
    )


def _entries_from_parsed(feed_id: str, parsed: ParsedFeed) -> list[Entry]:
    return [
        Entry(
            id=make_entry_id(feed_id, entry),
            feed_id=feed_id,
            title=entry.title,
            summary=entry.summary,
            author=entry.author,
            url=entry.url,
            published_at=entry.published_at,
            is_read=False,
            is_starred=False,
            tag_ids=[],
            reader_html=entry.raw_html,
            web_preview=entry.url,
            related_entry_ids=[],
            note="",
            summary_text="",
            translation_html=None,
            translation_status="idle",
        )
        for entry in parsed.entries
    ]


def _update_sync_metadata(feed_id: str, response: FetchResponse | None, *, status: str) -> None:
    update = require_db_function("update_feed_sync_metadata")
    kwargs: dict[str, Any] = {
        "feed_id": feed_id,
        "last_fetched_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "etag": response.etag if response else None,
        "last_modified": response.last_modified if response else None,
        "status": status,
    }
    update(**kwargs)
