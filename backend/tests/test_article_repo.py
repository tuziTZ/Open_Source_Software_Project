from app.schemas.entry import Entry
from app.schemas.feed import Feed
from db import (
    delete_article,
    get_article,
    get_article_content,
    init_db,
    list_articles,
    mark_article_read,
    mark_article_starred,
    save_article,
    save_article_content,
    save_articles,
    save_feed,
    search_articles,
    update_article_note,
)


def test_save_and_get_article(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)

    article = _article()

    save_article(article, db_path)

    assert get_article("article-1", db_path) == article


def test_save_article_updates_existing_row(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)

    updated = _article(title="Updated title", is_read=True, reader_html="<p>Updated</p>")

    save_article(updated, db_path)

    saved = get_article("article-1", db_path)
    assert saved is not None
    assert saved.title == "Updated title"
    assert saved.is_read is True
    assert saved.reader_html == "<p>Hello Mercury</p>"


def test_save_article_preserves_raw_html_for_cleaner(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)

    article = _article(reader_html="<main><p>Hello Mercury</p></main>")
    save_article(article, db_path)

    content = get_article_content("article-1", db_path)
    assert content is not None
    assert content.raw_html == "<main><p>Hello Mercury</p></main>"
    assert content.cleaned_html == ""
    assert get_article("article-1", db_path) == article


def test_save_article_does_not_overwrite_existing_cleaned_content(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(reader_html="<main><p>Original raw</p></main>"), db_path)
    save_article_content(
        article_id="article-1",
        raw_html="<main><p>Original raw</p></main>",
        cleaned_html="<p>Cleaned content</p>",
        cleaned_markdown="Cleaned content",
        plain_text="Cleaned content",
        db_path=db_path,
        content_hash="hash-1",
    )

    save_article(
        _article(title="Updated title", reader_html="<main><p>New raw</p></main>"),
        db_path,
    )

    content = get_article_content("article-1", db_path)
    assert content is not None
    assert content.raw_html == "<main><p>Original raw</p></main>"
    assert content.cleaned_html == "<p>Cleaned content</p>"
    assert get_article("article-1", db_path).reader_html == "<p>Cleaned content</p>"


def test_save_articles_batches_multiple_entries(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    first = _article()
    second = _article(
        article_id="article-2",
        title="Second article",
        published_at="2026-05-24T08:00:00Z",
        url="https://example.com/articles/2",
    )

    save_articles([first, second], db_path)

    assert list_articles(db_path=db_path) == [first, second]


def test_get_missing_article_returns_none(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    assert get_article("missing", db_path) is None


def test_list_articles_returns_articles_newest_first(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    older = _article(
        article_id="article-1",
        title="Older",
        published_at="2026-05-24T08:00:00Z",
    )
    newer = _article(
        article_id="article-2",
        title="Newer",
        published_at="2026-05-25T08:00:00Z",
        url="https://example.com/articles/2",
    )
    save_article(older, db_path)
    save_article(newer, db_path)

    assert list_articles(db_path=db_path) == [newer, older]


def test_list_articles_filters_by_feed(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_feed(
        Feed(
            id="feed-2",
            title="Other Feed",
            site_url="https://other.example.com",
            feed_url="https://other.example.com/feed.xml",
            unread_count=0,
            status="idle",
        ),
        db_path,
    )
    first_feed_article = _article()
    second_feed_article = _article(
        article_id="article-2",
        feed_id="feed-2",
        url="https://example.com/articles/2",
    )
    save_article(first_feed_article, db_path)
    save_article(second_feed_article, db_path)

    assert list_articles(feed_id="feed-1", db_path=db_path) == [first_feed_article]


def test_save_article_content_updates_reader_html(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    article = _article(reader_html="")
    save_article(article, db_path)

    save_article_content(
        article_id="article-1",
        raw_html="<main><p>Hello Mercury</p></main>",
        cleaned_html="<p>Hello Mercury</p>",
        cleaned_markdown="Hello Mercury",
        plain_text="Hello Mercury",
        db_path=db_path,
        content_hash="hash-1",
    )

    assert get_article("article-1", db_path) == _article(reader_html="<p>Hello Mercury</p>")

    content = get_article_content("article-1", db_path)
    assert content is not None
    assert content.raw_html == "<main><p>Hello Mercury</p></main>"
    assert content.cleaned_markdown == "Hello Mercury"
    assert content.content_hash == "hash-1"


def test_article_state_updates_and_delete(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)

    assert mark_article_read("article-1", True, db_path) is True
    assert mark_article_starred("article-1", True, db_path) is True
    assert update_article_note("article-1", "Keep this", db_path) is True

    updated = get_article("article-1", db_path)
    assert updated is not None
    assert updated.is_read is True
    assert updated.is_starred is True
    assert updated.note == "Keep this"

    assert delete_article("article-1", db_path) is True
    assert get_article("article-1", db_path) is None


def test_search_articles_uses_cleaned_plain_text(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    article = _article()
    save_article(article, db_path)
    save_article_content(
        article_id="article-1",
        raw_html="<p>Local-first RSS</p>",
        cleaned_html="<p>Local-first RSS</p>",
        cleaned_markdown="Local-first RSS",
        plain_text="Local-first RSS",
        db_path=db_path,
    )

    results = search_articles("RSS", db_path=db_path)
    assert [article.id for article in results] == [article.id]


def test_article_search_projection_updates_when_article_changes(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(title="Old title"), db_path)

    assert [article.id for article in search_articles("Old", db_path=db_path)] == ["article-1"]

    save_article(_article(title="New title"), db_path)

    assert [article.id for article in search_articles("New", db_path=db_path)] == ["article-1"]
    assert search_articles("Old", db_path=db_path) == []


def _feed() -> Feed:
    return Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )


def _article(
    article_id: str = "article-1",
    feed_id: str = "feed-1",
    title: str = "First article",
    published_at: str = "2026-05-25T08:00:00Z",
    is_read: bool = False,
    reader_html: str = "<p>Hello Mercury</p>",
    url: str = "https://example.com/articles/1",
) -> Entry:
    return Entry(
        id=article_id,
        feed_id=feed_id,
        title=title,
        summary="Short summary",
        author="Mercury Team",
        url=url,
        published_at=published_at,
        is_read=is_read,
        is_starred=False,
        tag_ids=[],
        reader_html=reader_html,
        web_preview="",
        related_entry_ids=[],
        note="",
        summary_text="",
        translation_html=None,
        translation_status="idle",
    )
