import sqlite3
from pathlib import Path

from app.schemas.feed import Feed
from db.connection import connection


def save_feed(feed: Feed, db_path: Path | str | None = None) -> Feed:
    with connection(db_path) as conn:
        with conn:
            _save_feed(conn, feed)
    return feed


def save_feeds(feeds: list[Feed], db_path: Path | str | None = None) -> list[Feed]:
    with connection(db_path) as conn:
        with conn:
            for feed in feeds:
                _save_feed(conn, feed)
    return feeds


def get_feed(feed_id: str, db_path: Path | str | None = None) -> Feed | None:
    with connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                feeds.id,
                feeds.title,
                feeds.site_url,
                feeds.feed_url,
                feeds.status,
                COUNT(articles.id) FILTER (WHERE articles.is_read = 0) AS unread_count
            FROM feeds
            LEFT JOIN articles ON articles.feed_id = feeds.id
            WHERE feeds.id = ?
            GROUP BY feeds.id
            """,
            (feed_id,),
        ).fetchone()

    if row is None:
        return None

    return _row_to_feed(row)


def delete_feed(feed_id: str, db_path: Path | str | None = None) -> bool:
    with connection(db_path) as conn:
        with conn:
            cursor = conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
    return cursor.rowcount > 0


def update_feed_sync_metadata(
    feed_id: str,
    last_fetched_at: str,
    etag: str | None,
    last_modified: str | None,
    status: str,
    db_path: Path | str | None = None,
) -> bool:
    """Update HTTP sync metadata after the feed engine fetches a feed."""
    with connection(db_path) as conn:
        with conn:
            cursor = conn.execute(
                """
                UPDATE feeds
                SET last_fetched_at = ?,
                    etag = ?,
                    last_modified = ?,
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (last_fetched_at, etag, last_modified, status, feed_id),
            )
    return cursor.rowcount > 0


def get_feed_sync_metadata(
    feed_id: str,
    db_path: Path | str | None = None,
) -> dict[str, str | None] | None:
    """Return HTTP sync metadata used by the feed engine for conditional fetches."""
    with connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                last_fetched_at,
                etag,
                last_modified
            FROM feeds
            WHERE id = ?
            """,
            (feed_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "last_fetched_at": row["last_fetched_at"],
        "etag": row["etag"],
        "last_modified": row["last_modified"],
    }


def query_feeds(
    keyword: str | None = None,
    db_path: Path | str | None = None,
) -> list[Feed]:
    sql = """
        SELECT
            feeds.id,
            feeds.title,
            feeds.site_url,
            feeds.feed_url,
            feeds.status,
            COUNT(articles.id) FILTER (WHERE articles.is_read = 0) AS unread_count
        FROM feeds
        LEFT JOIN articles ON articles.feed_id = feeds.id
    """
    params: tuple[str, ...] = ()

    if keyword:
        sql += """
            WHERE feeds.title LIKE ?
                OR feeds.site_url LIKE ?
                OR feeds.feed_url LIKE ?
        """
        like_keyword = f"%{keyword}%"
        params = (like_keyword, like_keyword, like_keyword)

    sql += """
        GROUP BY feeds.id
        ORDER BY feeds.title COLLATE NOCASE ASC
    """

    with connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_row_to_feed(row) for row in rows]


def _row_to_feed(row: sqlite3.Row) -> Feed:
    return Feed(
        id=row["id"],
        title=row["title"],
        site_url=row["site_url"],
        feed_url=row["feed_url"],
        unread_count=row["unread_count"],
        status=row["status"],
    )


def _save_feed(conn: sqlite3.Connection, feed: Feed) -> None:
    conn.execute(
        """
        INSERT INTO feeds (
            id,
            title,
            site_url,
            feed_url,
            status,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            site_url = excluded.site_url,
            feed_url = excluded.feed_url,
            status = excluded.status,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            feed.id,
            feed.title,
            feed.site_url,
            feed.feed_url,
            feed.status,
        ),
    )
