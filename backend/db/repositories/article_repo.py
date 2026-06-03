import sqlite3
from pathlib import Path

from app.schemas.content import ArticleContent
from app.schemas.entry import Entry
from db.connection import connection

READER_HTML_SQL = """
COALESCE(NULLIF(article_content.cleaned_html, ''), article_content.raw_html, '') AS reader_html
"""


def save_article(entry: Entry, db_path: Path | str | None = None) -> Entry:
    """Upsert one article metadata row and its current reader HTML projection."""
    with connection(db_path) as conn:
        with conn:
            _save_article(conn, entry)
    return entry


def save_articles(entries: list[Entry], db_path: Path | str | None = None) -> list[Entry]:
    """Upsert many articles in one transaction for feed sync batches."""
    with connection(db_path) as conn:
        with conn:
            for entry in entries:
                _save_article(conn, entry)
    return entries


def get_article(article_id: str, db_path: Path | str | None = None) -> Entry | None:
    """Return one article with content, tags, and latest successful agent outputs."""
    with connection(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT
                articles.id,
                articles.feed_id,
                articles.title,
                articles.summary,
                articles.author,
                articles.url,
                articles.published_at,
                articles.is_read,
                articles.is_starred,
                articles.note,
                {READER_HTML_SQL},
                (
                    SELECT GROUP_CONCAT(tag_id)
                    FROM article_tags
                    WHERE article_tags.article_id = articles.id
                ) AS tag_ids,
                latest_summary.output_text AS summary_text,
                latest_translation.output_text AS translation_html,
                latest_translation.status AS translation_status
            FROM articles
            LEFT JOIN article_content ON article_content.article_id = articles.id
            LEFT JOIN agent_runs AS latest_summary
                ON latest_summary.id = (
                    SELECT id
                    FROM agent_runs
                    WHERE article_id = articles.id
                        AND agent_type = 'summary'
                        AND status = 'success'
                    ORDER BY finished_at DESC, started_at DESC
                    LIMIT 1
                )
            LEFT JOIN agent_runs AS latest_translation
                ON latest_translation.id = (
                    SELECT id
                    FROM agent_runs
                    WHERE article_id = articles.id
                        AND agent_type = 'translation'
                        AND status = 'success'
                    ORDER BY finished_at DESC, started_at DESC
                    LIMIT 1
                )
            WHERE articles.id = ?
            """,
            (article_id,),
        ).fetchone()

    if row is None:
        return None

    return _row_to_entry(row)


def list_articles(
    feed_id: str | None = None,
    tag_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Path | str | None = None,
) -> list[Entry]:
    """List articles, optionally filtered by feed or tag, newest first."""
    sql = f"""
        SELECT
            articles.id,
            articles.feed_id,
            articles.title,
            articles.summary,
            articles.author,
            articles.url,
            articles.published_at,
            articles.is_read,
            articles.is_starred,
            articles.note,
            {READER_HTML_SQL},
            (
                SELECT GROUP_CONCAT(tag_id)
                FROM article_tags
                WHERE article_tags.article_id = articles.id
            ) AS tag_ids,
            latest_summary.output_text AS summary_text,
            latest_translation.output_text AS translation_html,
            latest_translation.status AS translation_status
        FROM articles
        LEFT JOIN article_content ON article_content.article_id = articles.id
        LEFT JOIN agent_runs AS latest_summary
            ON latest_summary.id = (
                SELECT id
                FROM agent_runs
                WHERE article_id = articles.id
                    AND agent_type = 'summary'
                    AND status = 'success'
                ORDER BY finished_at DESC, started_at DESC
                LIMIT 1
            )
        LEFT JOIN agent_runs AS latest_translation
            ON latest_translation.id = (
                SELECT id
                FROM agent_runs
                WHERE article_id = articles.id
                    AND agent_type = 'translation'
                    AND status = 'success'
                ORDER BY finished_at DESC, started_at DESC
                LIMIT 1
            )
    """
    params: list[str | int] = []
    where_clauses: list[str] = []

    if feed_id is not None:
        where_clauses.append("articles.feed_id = ?")
        params.append(feed_id)
    if tag_id is not None:
        sql += " INNER JOIN article_tags ON article_tags.article_id = articles.id"
        where_clauses.append("article_tags.tag_id = ?")
        params.append(tag_id)

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += " ORDER BY articles.published_at DESC, articles.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_row_to_entry(row) for row in rows]


def save_article_content(
    article_id: str,
    raw_html: str,
    cleaned_html: str,
    cleaned_markdown: str,
    plain_text: str,
    db_path: Path | str | None = None,
    content_hash: str | None = None,
) -> None:
    """Upsert cleaned article content written by the content cleaner pipeline."""
    with connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO article_content (
                    article_id,
                    raw_html,
                    cleaned_html,
                    cleaned_markdown,
                    plain_text,
                    content_hash,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(article_id) DO UPDATE SET
                    raw_html = excluded.raw_html,
                    cleaned_html = excluded.cleaned_html,
                    cleaned_markdown = excluded.cleaned_markdown,
                    plain_text = excluded.plain_text,
                    content_hash = excluded.content_hash,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    article_id,
                    raw_html,
                    cleaned_html,
                    cleaned_markdown,
                    plain_text,
                    content_hash,
                ),
            )
            conn.execute(
                """
                INSERT INTO article_search (
                    article_id,
                    plain_text,
                    updated_at
                )
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(article_id) DO UPDATE SET
                    plain_text = excluded.plain_text,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (article_id, plain_text),
            )


def get_article_content(
    article_id: str,
    db_path: Path | str | None = None,
) -> ArticleContent | None:
    """Return raw and cleaned content for the content cleaner pipeline."""
    with connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                article_id,
                raw_html,
                cleaned_html,
                cleaned_markdown,
                plain_text,
                content_hash
            FROM article_content
            WHERE article_id = ?
            """,
            (article_id,),
        ).fetchone()

    if row is None:
        return None

    return ArticleContent(
        article_id=row["article_id"],
        raw_html=row["raw_html"],
        cleaned_html=row["cleaned_html"],
        cleaned_markdown=row["cleaned_markdown"],
        plain_text=row["plain_text"],
        content_hash=row["content_hash"],
    )


def delete_article(article_id: str, db_path: Path | str | None = None) -> bool:
    """Delete one article and cascade its content, tags, and agent records."""
    with connection(db_path) as conn:
        with conn:
            cursor = conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    return cursor.rowcount > 0


def mark_article_read(
    article_id: str,
    is_read: bool,
    db_path: Path | str | None = None,
) -> bool:
    """Set the read/unread state for one article."""
    return _update_article_flag(article_id, "is_read", is_read, db_path)


def mark_article_starred(
    article_id: str,
    is_starred: bool,
    db_path: Path | str | None = None,
) -> bool:
    """Set the starred state for one article."""
    return _update_article_flag(article_id, "is_starred", is_starred, db_path)


def update_article_note(
    article_id: str,
    note: str,
    db_path: Path | str | None = None,
) -> bool:
    """Update the local note attached to one article."""
    with connection(db_path) as conn:
        with conn:
            cursor = conn.execute(
                """
                UPDATE articles
                SET note = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (note, article_id),
            )
    return cursor.rowcount > 0


def search_articles(
    keyword: str,
    limit: int = 50,
    offset: int = 0,
    db_path: Path | str | None = None,
) -> list[Entry]:
    """Search articles by title, summary, or cleaned plain text projection."""
    like_keyword = f"%{keyword}%"
    match_keyword = keyword.replace('"', '""')
    sql = f"""
        SELECT DISTINCT
            articles.id,
            articles.feed_id,
            articles.title,
            articles.summary,
            articles.author,
            articles.url,
            articles.published_at,
            articles.is_read,
            articles.is_starred,
            articles.note,
            {READER_HTML_SQL},
            (
                SELECT GROUP_CONCAT(tag_id)
                FROM article_tags
                WHERE article_tags.article_id = articles.id
            ) AS tag_ids,
            latest_summary.output_text AS summary_text,
            latest_translation.output_text AS translation_html,
            latest_translation.status AS translation_status
        FROM articles
        LEFT JOIN article_content ON article_content.article_id = articles.id
        LEFT JOIN article_search ON article_search.article_id = articles.id
        LEFT JOIN article_fts ON article_fts.rowid = article_search.rowid
        LEFT JOIN agent_runs AS latest_summary
            ON latest_summary.id = (
                SELECT id
                FROM agent_runs
                WHERE article_id = articles.id
                    AND agent_type = 'summary'
                    AND status = 'success'
                ORDER BY finished_at DESC, started_at DESC
                LIMIT 1
            )
        LEFT JOIN agent_runs AS latest_translation
            ON latest_translation.id = (
                SELECT id
                FROM agent_runs
                WHERE article_id = articles.id
                    AND agent_type = 'translation'
                    AND status = 'success'
                ORDER BY finished_at DESC, started_at DESC
                LIMIT 1
            )
        WHERE article_fts MATCH ?
        ORDER BY articles.published_at DESC, articles.created_at DESC
        LIMIT ? OFFSET ?
    """
    with connection(db_path) as conn:
        try:
            rows = conn.execute(sql, (match_keyword, limit, offset)).fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute(
                f"""
                SELECT DISTINCT
                    articles.id,
                    articles.feed_id,
                    articles.title,
                    articles.summary,
                    articles.author,
                    articles.url,
                    articles.published_at,
                    articles.is_read,
                    articles.is_starred,
                    articles.note,
                    {READER_HTML_SQL},
                    (
                        SELECT GROUP_CONCAT(tag_id)
                        FROM article_tags
                        WHERE article_tags.article_id = articles.id
                    ) AS tag_ids,
                    latest_summary.output_text AS summary_text,
                    latest_translation.output_text AS translation_html,
                    latest_translation.status AS translation_status
                FROM articles
                LEFT JOIN article_content ON article_content.article_id = articles.id
                LEFT JOIN article_search ON article_search.article_id = articles.id
                LEFT JOIN agent_runs AS latest_summary
                    ON latest_summary.id = (
                        SELECT id
                        FROM agent_runs
                        WHERE article_id = articles.id
                            AND agent_type = 'summary'
                            AND status = 'success'
                        ORDER BY finished_at DESC, started_at DESC
                        LIMIT 1
                    )
                LEFT JOIN agent_runs AS latest_translation
                    ON latest_translation.id = (
                        SELECT id
                        FROM agent_runs
                        WHERE article_id = articles.id
                            AND agent_type = 'translation'
                            AND status = 'success'
                        ORDER BY finished_at DESC, started_at DESC
                        LIMIT 1
                    )
                WHERE articles.title LIKE ?
                    OR articles.summary LIKE ?
                    OR article_search.plain_text LIKE ?
                ORDER BY articles.published_at DESC, articles.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (like_keyword, like_keyword, like_keyword, limit, offset),
            ).fetchall()

    return [_row_to_entry(row) for row in rows]


def _row_to_entry(row: sqlite3.Row) -> Entry:
    tag_ids = []
    if "tag_ids" in row.keys() and row["tag_ids"]:
        tag_ids = row["tag_ids"].split(",")

    return Entry(
        id=row["id"],
        feed_id=row["feed_id"],
        title=row["title"],
        summary=row["summary"],
        author=row["author"],
        url=row["url"],
        published_at=row["published_at"] or "",
        is_read=bool(row["is_read"]),
        is_starred=bool(row["is_starred"]),
        tag_ids=tag_ids,
        reader_html=row["reader_html"] or "",
        web_preview="",
        related_entry_ids=[],
        note=row["note"],
        summary_text=row["summary_text"] or "",
        translation_html=row["translation_html"],
        translation_status=row["translation_status"] or "idle",
    )


def _save_article(conn: sqlite3.Connection, entry: Entry) -> None:
    conn.execute(
        """
        INSERT INTO articles (
            id,
            feed_id,
            title,
            summary,
            author,
            url,
            published_at,
            is_read,
            is_starred,
            note,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            feed_id = excluded.feed_id,
            title = excluded.title,
            summary = excluded.summary,
            author = excluded.author,
            url = excluded.url,
            published_at = excluded.published_at,
            is_read = excluded.is_read,
            is_starred = excluded.is_starred,
            note = excluded.note,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            entry.id,
            entry.feed_id,
            entry.title,
            entry.summary,
            entry.author,
            entry.url,
            entry.published_at,
            int(entry.is_read),
            int(entry.is_starred),
            entry.note,
        ),
    )
    conn.execute(
        """
        INSERT INTO article_content (
            article_id,
            raw_html,
            cleaned_html,
            updated_at
        )
        VALUES (?, ?, '', CURRENT_TIMESTAMP)
        ON CONFLICT(article_id) DO NOTHING
        """,
        (entry.id, entry.reader_html),
    )
    conn.execute(
        """
        INSERT INTO article_search (
            article_id,
            title,
            summary,
            updated_at
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(article_id) DO UPDATE SET
            title = excluded.title,
            summary = excluded.summary,
            updated_at = CURRENT_TIMESTAMP
        """,
        (entry.id, entry.title, entry.summary),
    )


def _update_article_flag(
    article_id: str,
    column: str,
    value: bool,
    db_path: Path | str | None = None,
) -> bool:
    with connection(db_path) as conn:
        with conn:
            if column == "is_read":
                cursor = conn.execute(
                    """
                    UPDATE articles
                    SET is_read = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (int(value), article_id),
                )
            elif column == "is_starred":
                cursor = conn.execute(
                    """
                    UPDATE articles
                    SET is_starred = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (int(value), article_id),
                )
            else:
                raise ValueError(f"Unsupported article flag: {column}")
    return cursor.rowcount > 0
