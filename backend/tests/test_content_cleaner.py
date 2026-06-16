"""Tests for the content_cleaner module."""

import pytest
from fastapi.testclient import TestClient

from content_cleaner.schemas import CleanContentRequest
from content_cleaner.service import clean_html

# ── Test fixtures (HTML snippets) ────────────────────────────────


@pytest.fixture
def typical_blog_html() -> str:
    return """\
<html>
<body>
  <article>
    <h1>Introducing Mercury RSS</h1>
    <p>Mercury is a <strong>local-first</strong> RSS reader that runs on your machine.</p>
    <p>It supports:</p>
    <ul>
      <li>AI summarisation</li>
      <li>Translation to Chinese</li>
      <li>Offline reading</li>
    </ul>
    <blockquote>
      <p>"The best RSS reader I've ever used." — A happy user</p>
    </blockquote>
    <p>
      <a href="/docs/install">Installation guide</a>
      —
      <img src="/img/screenshot.png" alt="Screenshot" width="800" height="450">
    </p>
  </article>
</body>
</html>"""


@pytest.fixture
def code_heavy_html() -> str:
    return """\
<html>
<body>
  <article>
    <h1>Building a FastAPI Extension</h1>
    <p>Start by installing the dependencies:</p>
    <pre><code class="language-bash">pip install fastapi uvicorn
# or with uv
uv add fastapi uvicorn</code></pre>
    <p>Then create your first route:</p>
    <pre><code class="language-python">from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"hello": "world"}</code></pre>
    <p>That's it! Run with <code>uvicorn main:app</code>.</p>
  </article>
</body>
</html>"""


@pytest.fixture
def paywalled_html() -> str:
    return """\
<html>
<body>
  <article>
    <h1>Exclusive: The Future of AI</h1>
    <p>Artificial intelligence is advancing at an unprecedented pace.</p>
    <div class="paywall-overlay">
      <p>To continue reading, please subscribe.</p>
    </div>
  </article>
</body>
</html>"""


@pytest.fixture
def malicious_html() -> str:
    return """\
<html>
<body>
  <h1>Hello</h1>
  <script>alert('xss')</script>
  <p onclick="stealCookies()">Click me</p>
  <img src="https://evil.com/pixel.gif" width="1" height="1">
  <div onerror="fetch('/hijack')">safe text</div>
  <a href="javascript:void(0)">bad link</a>
</body>
</html>"""


@pytest.fixture
def relative_url_html() -> str:
    return """\
<html>
<body>
  <a href="/about">About</a>
  <a href="https://external.com/page">External</a>
  <img src="/images/logo.png" alt="Logo">
  <img src="//cdn.example.com/asset.jpg" alt="CDN">
</body>
</html>"""


# ── Unit tests for clean_html ────────────────────────────────────


class TestCleanHtmlBlogPost:
    def test_preserves_headings_and_paragraphs(self, typical_blog_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=typical_blog_html, source_url="https://example.com")
        )
        assert "Introducing Mercury RSS" in result.cleaned_html
        assert "Mercury" in result.plain_text
        assert "# Introducing Mercury RSS" in result.cleaned_markdown

    def test_preserves_lists_in_markdown(self, typical_blog_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=typical_blog_html, source_url="https://example.com")
        )
        # markdownify uses "*" for unordered list items
        assert "* AI summarisation" in result.cleaned_markdown
        assert "* Translation to Chinese" in result.cleaned_markdown

    def test_preserves_blockquote(self, typical_blog_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=typical_blog_html, source_url="https://example.com")
        )
        assert "happy user" in result.cleaned_markdown

    def test_preserves_strong_formatting(self, typical_blog_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=typical_blog_html, source_url="https://example.com")
        )
        assert "**local-first**" in result.cleaned_markdown


class TestCleanHtmlCodeHeavy:
    def test_preserves_code_blocks(self, code_heavy_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=code_heavy_html, source_url="https://example.com")
        )
        assert "pip install fastapi" in result.cleaned_markdown
        assert "from fastapi import FastAPI" in result.cleaned_markdown

    def test_preserves_inline_code(self, code_heavy_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=code_heavy_html, source_url="https://example.com")
        )
        # markdownify wraps inline code in backticks
        assert "`uvicorn main:app`" in result.cleaned_markdown


class TestCleanHtmlPaywalled:
    def test_returns_partial_content(self, paywalled_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=paywalled_html, source_url="https://example.com")
        )
        assert "The Future of AI" in result.plain_text
        # Paywall overlay text is still present (structural cleaning, not access control)
        assert "subscribe" in result.plain_text.lower()

    def test_paywalled_does_not_crash(self, paywalled_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=paywalled_html, source_url="https://example.com")
        )
        assert result.cleaned_html
        assert result.cleaned_markdown
        assert result.word_count > 0


class TestSanitization:
    def test_removes_script_tags(self, malicious_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=malicious_html, source_url="https://example.com")
        )
        # <script> tag must be gone; its text content may remain as plain text
        assert "<script" not in result.cleaned_html
        assert "</script>" not in result.cleaned_html

    def test_removes_inline_event_handlers(self, malicious_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=malicious_html, source_url="https://example.com")
        )
        assert "onclick" not in result.cleaned_html
        assert "onerror" not in result.cleaned_html

    def test_removes_tracking_pixels(self, malicious_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=malicious_html, source_url="https://example.com")
        )
        assert "pixel.gif" not in result.cleaned_html

    def test_removes_javascript_protocol_links(self, malicious_html: str) -> None:
        result = clean_html(
            CleanContentRequest(raw_html=malicious_html, source_url="https://example.com")
        )
        assert "javascript:" not in result.cleaned_html


class TestUrlResolution:
    def test_resolves_relative_href(self, relative_url_html: str) -> None:
        result = clean_html(
            CleanContentRequest(
                raw_html=relative_url_html,
                source_url="https://blog.example.com/posts/1",
            )
        )
        assert 'href="https://blog.example.com/about"' in result.cleaned_html

    def test_keeps_absolute_urls_untouched(self, relative_url_html: str) -> None:
        result = clean_html(
            CleanContentRequest(
                raw_html=relative_url_html,
                source_url="https://blog.example.com/posts/1",
            )
        )
        assert 'href="https://external.com/page"' in result.cleaned_html

    def test_resolves_relative_img_src(self, relative_url_html: str) -> None:
        result = clean_html(
            CleanContentRequest(
                raw_html=relative_url_html,
                source_url="https://blog.example.com/posts/1",
            )
        )
        assert 'src="https://blog.example.com/images/logo.png"' in result.cleaned_html

    def test_keeps_protocol_relative_urls_untouched(self, relative_url_html: str) -> None:
        result = clean_html(
            CleanContentRequest(
                raw_html=relative_url_html,
                source_url="https://blog.example.com/posts/1",
            )
        )
        assert "//cdn.example.com/asset.jpg" in result.cleaned_html


class TestWordCountAndReadingTime:
    def test_word_count(self) -> None:
        html = "<p>one two three four five</p>"
        result = clean_html(
            CleanContentRequest(raw_html=html, source_url="https://example.com")
        )
        assert result.word_count == 5

    def test_reading_time_minimum_one_minute(self) -> None:
        html = "<p>hello world</p>"
        result = clean_html(
            CleanContentRequest(raw_html=html, source_url="https://example.com")
        )
        assert result.reading_time_minutes == 1

    def test_reading_time_scales_with_word_count(self) -> None:
        words = "word " * 400  # 400 words → 2 minutes at 200 wpm
        html = f"<p>{words}</p>"
        result = clean_html(
            CleanContentRequest(raw_html=html, source_url="https://example.com")
        )
        assert result.word_count == 400
        assert result.reading_time_minutes == 2

    def test_empty_content(self) -> None:
        result = clean_html(
            CleanContentRequest(raw_html="", source_url="https://example.com")
        )
        assert result.word_count == 0
        assert result.reading_time_minutes == 1  # floor of 1


class TestContentHash:
    def test_same_input_same_hash(self) -> None:
        html = "<p>hello</p>"
        r1 = clean_html(CleanContentRequest(raw_html=html, source_url="https://a.com"))
        r2 = clean_html(CleanContentRequest(raw_html=html, source_url="https://b.com"))
        assert r1.content_hash == r2.content_hash

    def test_different_input_different_hash(self) -> None:
        r1 = clean_html(CleanContentRequest(raw_html="<p>a</p>", source_url="https://a.com"))
        r2 = clean_html(CleanContentRequest(raw_html="<p>b</p>", source_url="https://a.com"))
        assert r1.content_hash != r2.content_hash

    def test_hash_length(self) -> None:
        result = clean_html(
            CleanContentRequest(raw_html="<p>test</p>", source_url="https://a.com")
        )
        assert result.content_hash is not None
        assert len(result.content_hash) == 16


class TestArticleIdPassthrough:
    def test_article_id_returned_in_response(self) -> None:
        result = clean_html(
            CleanContentRequest(
                raw_html="<p>hi</p>",
                source_url="https://example.com",
                article_id="art-001",
            )
        )
        assert result.article_id == "art-001"

    def test_article_id_none_by_default(self) -> None:
        result = clean_html(
            CleanContentRequest(raw_html="<p>hi</p>", source_url="https://example.com")
        )
        assert result.article_id is None


# ── HTTP endpoint tests ──────────────────────────────────────────


class TestCleanEndpoint:
    def test_post_clean_returns_200(self, client: TestClient) -> None:
        response = client.post(
            "/content/clean",
            json={
                "raw_html": "<p>Hello world</p>",
                "source_url": "https://example.com",
            },
        )
        assert response.status_code == 200

    def test_post_clean_returns_cleaned_html(self, client: TestClient) -> None:
        response = client.post(
            "/content/clean",
            json={
                "raw_html": "<p>Hello <strong>world</strong></p>",
                "source_url": "https://example.com",
            },
        )
        data = response.json()
        assert "Hello" in data["cleaned_html"]
        assert "Hello **world**" == data["cleaned_markdown"].strip()
        assert data["word_count"] == 2

    def test_post_clean_sanitizes_script(self, client: TestClient) -> None:
        response = client.post(
            "/content/clean",
            json={
                "raw_html": "<h1>Safe</h1><script>alert(1)</script>",
                "source_url": "https://example.com",
            },
        )
        data = response.json()
        assert "<script" not in data["cleaned_html"]
        assert "</script>" not in data["cleaned_html"]
        # Script text content may remain as plain text after tag stripping
        assert "Safe" in data["cleaned_html"]

    def test_post_clean_returns_metadata(self, client: TestClient) -> None:
        response = client.post(
            "/content/clean",
            json={
                "raw_html": "<p>" + "hello " * 50 + "</p>",
                "source_url": "https://example.com",
            },
        )
        data = response.json()
        assert data["word_count"] == 50
        assert data["reading_time_minutes"] == 1
        assert data["content_hash"] is not None
        assert len(data["content_hash"]) == 16


class TestCleanStoredEndpoint:
    def test_get_nonexistent_article_returns_404(self, client: TestClient) -> None:
        response = client.get("/content/entries/nonexistent-id/clean")
        assert response.status_code == 404

    def test_clean_stored_article_success(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Clean a stored article end-to-end: reads raw HTML from DB, cleans, writes back."""
        import content_cleaner.service as cleaner_service
        from app.schemas.content import ArticleContent
        from app.schemas.entry import Entry

        fake_content = ArticleContent(
            article_id="art-001",
            raw_html="<article><h1>Hello</h1><p>World</p></article>",
            cleaned_html="",
            cleaned_markdown="",
            plain_text="",
            content_hash=None,
        )
        fake_entry = Entry(
            id="art-001",
            feed_id="feed-001",
            title="Test Article",
            summary="",
            author="",
            url="https://example.com/article",
            published_at="2026-01-01T00:00:00Z",
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

        saved: dict = {}

        def fake_save(**kwargs: object) -> None:
            saved.update(kwargs)

        monkeypatch.setattr(
            cleaner_service,
            "get_article_content",
            lambda aid: fake_content if aid == "art-001" else None,
        )
        monkeypatch.setattr(
            cleaner_service,
            "get_article",
            lambda aid: fake_entry if aid == "art-001" else None,
        )
        monkeypatch.setattr(cleaner_service, "save_article_content", fake_save)

        response = client.get("/content/entries/art-001/clean")
        assert response.status_code == 200

        data = response.json()
        assert data["article_id"] == "art-001"
        assert "Hello" in data["cleaned_html"]
        assert "World" in data["plain_text"]
        assert data["word_count"] == 2
        assert data["reading_time_minutes"] == 1
        assert data["content_hash"] is not None
        assert len(data["content_hash"]) == 16

        # Verify persistence call
        assert saved["article_id"] == "art-001"
        assert saved["raw_html"] == fake_content.raw_html
        assert saved["cleaned_html"] == data["cleaned_html"]
        assert saved["cleaned_markdown"] == data["cleaned_markdown"]
        assert saved["plain_text"] == data["plain_text"]
        assert saved["content_hash"] == data["content_hash"]

    def test_clean_stored_article_empty_body(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Article with empty raw HTML returns zero word count and floor reading time."""
        import content_cleaner.service as cleaner_service
        from app.schemas.content import ArticleContent
        from app.schemas.entry import Entry

        fake_content = ArticleContent(
            article_id="art-empty",
            raw_html="",
            cleaned_html="",
            cleaned_markdown="",
            plain_text="",
        )
        fake_entry = Entry(
            id="art-empty",
            feed_id="feed-001",
            title="Empty",
            summary="",
            author="",
            url="https://example.com/empty",
            published_at="2026-01-01T00:00:00Z",
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

        monkeypatch.setattr(
            cleaner_service,
            "get_article_content",
            lambda aid: fake_content if aid == "art-empty" else None,
        )
        monkeypatch.setattr(
            cleaner_service,
            "get_article",
            lambda aid: fake_entry if aid == "art-empty" else None,
        )
        monkeypatch.setattr(cleaner_service, "save_article_content", lambda **kw: None)

        response = client.get("/content/entries/art-empty/clean")
        assert response.status_code == 200

        data = response.json()
        assert data["word_count"] == 0
        assert data["reading_time_minutes"] == 1  # floor
        assert data["plain_text"] == ""

    def test_clean_stored_article_fetches_full_page_for_hnrss_metadata(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import content_cleaner.service as cleaner_service
        from app.schemas.content import ArticleContent
        from app.schemas.entry import Entry

        fake_content = ArticleContent(
            article_id="art-hn",
            raw_html="""
            <p>Article URL: <a href="https://example.com/full">https://example.com/full</a></p>
            <p>Comments URL: <a href="https://news.ycombinator.com/item?id=1">HN</a></p>
            <p>Points: 74</p>
            <p># Comments: 17</p>
            """,
            cleaned_html="",
            cleaned_markdown="",
            plain_text="",
        )
        fake_entry = Entry(
            id="art-hn",
            feed_id="feed-001",
            title="HN Article",
            summary="",
            author="",
            url="https://example.com/full",
            published_at="2026-01-01T00:00:00Z",
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

        class FakeHeaders:
            def get(self, name: str) -> str | None:
                return "text/html; charset=utf-8" if name == "Content-Type" else None

        class FakeResponse:
            url = "https://example.com/full"
            headers = FakeHeaders()

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return (
                    b"<html><body><nav>menu</nav><article>"
                    b"<h1>Real article title</h1><p>Real article body text.</p>"
                    b"</article></body></html>"
                )

        saved: dict = {}
        monkeypatch.setattr(
            cleaner_service,
            "get_article_content",
            lambda aid: fake_content if aid == "art-hn" else None,
        )
        monkeypatch.setattr(
            cleaner_service,
            "get_article",
            lambda aid: fake_entry if aid == "art-hn" else None,
        )
        monkeypatch.setattr(cleaner_service, "urlopen", lambda *args, **kwargs: FakeResponse())
        monkeypatch.setattr(cleaner_service, "save_article_content", lambda **kw: saved.update(kw))

        response = client.get("/content/entries/art-hn/clean")
        assert response.status_code == 200
        data = response.json()
        assert "Real article title" in data["cleaned_html"]
        assert "Real article body text." in data["cleaned_markdown"]
        assert "Article URL:" not in data["plain_text"]
        assert "Real article title" in saved["raw_html"]


class TestFetchStoredWebPageEndpoint:
    def test_get_nonexistent_article_returns_404(self, client: TestClient) -> None:
        response = client.get("/content/entries/nonexistent-id/web")
        assert response.status_code == 404

    def test_rejects_non_http_article_url(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import content_cleaner.service as cleaner_service
        from app.schemas.entry import Entry

        fake_entry = Entry(
            id="art-file",
            feed_id="feed-001",
            title="Local Article",
            summary="",
            author="",
            url="file:///tmp/article.html",
            published_at="2026-01-01T00:00:00Z",
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

        monkeypatch.setattr(
            cleaner_service,
            "get_article",
            lambda aid: fake_entry if aid == "art-file" else None,
        )

        response = client.get("/content/entries/art-file/web")
        assert response.status_code == 409

    def test_fetches_html_and_injects_base_url(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import content_cleaner.service as cleaner_service
        from app.schemas.entry import Entry

        fake_entry = Entry(
            id="art-web",
            feed_id="feed-001",
            title="Web Article",
            summary="",
            author="",
            url="https://example.com/articles/one",
            published_at="2026-01-01T00:00:00Z",
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

        class FakeHeaders:
            def get(self, name: str) -> str | None:
                return "text/html; charset=utf-8" if name == "Content-Type" else None

        class FakeResponse:
            url = "https://example.com/articles/one?utm=no"
            headers = FakeHeaders()

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return (
                    b"<html><head><title>Hi</title></head>"
                    b"<body><img src='image.png'></body></html>"
                )

        monkeypatch.setattr(
            cleaner_service,
            "get_article",
            lambda aid: fake_entry if aid == "art-web" else None,
        )
        monkeypatch.setattr(cleaner_service, "urlopen", lambda *args, **kwargs: FakeResponse())

        response = client.get("/content/entries/art-web/web")
        assert response.status_code == 200
        data = response.json()
        assert data["article_id"] == "art-web"
        assert data["final_url"] == "https://example.com/articles/one?utm=no"
        assert '<base href="https://example.com/articles/one?utm=no"/>' in data["html"]
