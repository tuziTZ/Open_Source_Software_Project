from app.schemas.feed import Feed
from db import (
    delete_feed,
    get_feed,
    get_feed_sync_metadata,
    init_db,
    query_feeds,
    save_feed,
    save_feeds,
    update_feed_sync_metadata,
)


def test_save_and_get_feed(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    feed = Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )

    save_feed(feed, db_path)

    assert get_feed("feed-1", db_path) == feed


def test_get_missing_feed_returns_none(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    assert get_feed("missing", db_path) is None


def test_query_feeds_returns_all_feeds_ordered_by_title(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    mercury = Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )
    alpha = Feed(
        id="feed-2",
        title="Alpha Notes",
        site_url="https://alpha.example.com",
        feed_url="https://alpha.example.com/feed.xml",
        unread_count=0,
        status="idle",
    )
    save_feed(mercury, db_path)
    save_feed(alpha, db_path)

    assert query_feeds(db_path=db_path) == [alpha, mercury]


def test_query_feeds_filters_by_keyword(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    mercury = Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )
    alpha = Feed(
        id="feed-2",
        title="Alpha Notes",
        site_url="https://alpha.example.com",
        feed_url="https://alpha.example.com/feed.xml",
        unread_count=0,
        status="idle",
    )
    save_feed(mercury, db_path)
    save_feed(alpha, db_path)

    assert query_feeds("Mercury", db_path) == [mercury]


def test_save_feeds_batches_multiple_feeds(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    mercury = Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )
    alpha = Feed(
        id="feed-2",
        title="Alpha Notes",
        site_url="https://alpha.example.com",
        feed_url="https://alpha.example.com/feed.xml",
        unread_count=0,
        status="idle",
    )

    save_feeds([mercury, alpha], db_path)

    assert query_feeds(db_path=db_path) == [alpha, mercury]


def test_delete_feed_removes_feed(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    feed = Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )
    save_feed(feed, db_path)

    assert delete_feed("feed-1", db_path) is True
    assert get_feed("feed-1", db_path) is None


def test_update_feed_sync_metadata(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    feed = Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )
    save_feed(feed, db_path)

    assert (
        update_feed_sync_metadata(
            feed_id="feed-1",
            last_fetched_at="2026-05-25T12:00:00Z",
            etag="etag-1",
            last_modified="Mon, 25 May 2026 12:00:00 GMT",
            status="success",
            db_path=db_path,
        )
        is True
    )
    assert get_feed("feed-1", db_path).status == "success"

    assert get_feed_sync_metadata("feed-1", db_path) == {
        "last_fetched_at": "2026-05-25T12:00:00Z",
        "etag": "etag-1",
        "last_modified": "Mon, 25 May 2026 12:00:00 GMT",
    }


def test_get_feed_sync_metadata_returns_none_for_missing_feed(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    assert get_feed_sync_metadata("missing", db_path) is None
