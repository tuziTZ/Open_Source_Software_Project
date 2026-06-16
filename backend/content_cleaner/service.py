import hashlib
import logging
import math
import sqlite3
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from bleach import clean as bleach_clean
from bs4 import BeautifulSoup
from fastapi import HTTPException
from markdownify import markdownify as md

from app.schemas.content import ArticleContent
from db import get_article, get_article_content, save_article_content

from .schemas import CleanContentRequest, CleanContentResponse, WebPageResponse

logger = logging.getLogger(__name__)

# ── bleach sanitizer allowlists ──────────────────────────────────

ALLOWED_TAGS = [
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "caption",
    "code",
    "col",
    "colgroup",
    "dd",
    "del",
    "div",
    "dl",
    "dt",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "ins",
    "li",
    "ol",
    "p",
    "pre",
    "q",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
]

ALLOWED_ATTRIBUTES = {
    "*": ["id", "class", "title", "lang", "dir"],
    "a": ["href", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "col": ["span"],
    "code": ["class"],
    "pre": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# Attributes whose values should be resolved to absolute URLs
URL_ATTRS: dict[str, str] = {
    "a": "href",
    "img": "src",
    "source": "src",
    "video": "src",
    "audio": "src",
}

READING_WPM = 200


# ── Public API ───────────────────────────────────────────────────

def clean_html(request: CleanContentRequest) -> CleanContentResponse:
    """Run the full HTML cleaning pipeline.

    Steps: parse → sanitize → remove trackers → resolve URLs →
           extract cleaned HTML / plain text → convert to Markdown →
           compute word count / reading time / content hash.
    """
    raw_html = request.raw_html

    # 1. Parse and prefer the actual article container when the source is a full web page.
    soup = BeautifulSoup(raw_html, "lxml")
    soup = _extract_reader_candidate(soup)

    # 2. Sanitize — strip scripts, event handlers, dangerous markup
    sanitized = bleach_clean(
        str(soup),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

    # 3. Re-parse so we can do structural tweaks
    clean_soup = BeautifulSoup(sanitized, "lxml")

    # 4. Remove tracking pixels (tiny / hidden images)
    _remove_tracking_pixels(clean_soup)

    # 5. Resolve relative URLs against the source URL
    if request.source_url:
        _resolve_urls(clean_soup, request.source_url)

    # 6. Produce output formats
    cleaned_html = str(clean_soup)
    plain_text = clean_soup.get_text(separator="\n", strip=True)

    # 7. Convert to Markdown
    cleaned_markdown = md(
        cleaned_html,
        heading_style="ATX",
        strip=["script", "style"],
    )

    # 8. Compute metadata
    word_count = _count_words(plain_text)
    reading_time_minutes = max(1, math.ceil(word_count / READING_WPM))
    content_hash = hashlib.sha256(raw_html.encode()).hexdigest()[:16]

    return CleanContentResponse(
        article_id=request.article_id,
        cleaned_html=cleaned_html,
        cleaned_markdown=cleaned_markdown,
        plain_text=plain_text,
        content_hash=content_hash,
        word_count=word_count,
        reading_time_minutes=reading_time_minutes,
    )


def clean_stored_article(article_id: str) -> CleanContentResponse:
    """Read article HTML, preferring the canonical URL when feed HTML is only metadata."""
    try:
        content = get_article_content(article_id)
    except sqlite3.OperationalError as err:
        raise HTTPException(
            status_code=404,
            detail=f"Article '{article_id}' not found",
        ) from err

    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Article '{article_id}' not found",
        )

    entry = get_article(article_id)
    source_url = entry.url if entry else ""
    raw_html = content.raw_html
    if entry is not None and _should_fetch_reader_source(content.raw_html):
        fetched = _try_fetch_web_page(entry.url)
        if fetched is not None:
            raw_html = fetched.html
            source_url = fetched.final_url

    result = clean_html(
        CleanContentRequest(
            raw_html=raw_html,
            source_url=source_url,
            article_id=article_id,
        )
    )

    save_article_content(
        article_id=article_id,
        raw_html=raw_html,
        cleaned_html=result.cleaned_html,
        cleaned_markdown=result.cleaned_markdown,
        plain_text=result.plain_text,
        content_hash=result.content_hash or "",
    )

    logger.info(
        "Cleaned and stored article %s (%d words)",
        article_id,
        result.word_count,
    )
    return result


def fetch_entry_web_page(article_id: str, timeout_seconds: float = 15.0) -> WebPageResponse:
    """Fetch the article's canonical URL and return HTML suitable for iframe srcDoc."""
    try:
        entry = get_article(article_id)
    except sqlite3.OperationalError as err:
        raise HTTPException(
            status_code=404,
            detail=f"Article '{article_id}' not found",
        ) from err

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Article '{article_id}' not found",
        )

    fetched = _try_fetch_web_page(entry.url, timeout_seconds=timeout_seconds)
    if fetched is None:
        raise HTTPException(status_code=502, detail="Web page request failed")

    html = _inject_base_url(fetched.html, fetched.final_url)
    return WebPageResponse(
        article_id=article_id,
        url=fetched.url,
        final_url=fetched.final_url,
        content_type=fetched.content_type,
        html=html,
    )


def _try_fetch_web_page(url: str, timeout_seconds: float = 15.0) -> WebPageResponse | None:
    url = _validate_web_url(url)
    headers = {
        "User-Agent": "Lumen/0.1 web-preview",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    request = Request(url, headers=headers)

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type")
            final_url = response.url
    except HTTPError as exc:
        logger.info("Web page server returned HTTP %s for %s", exc.code, url)
        return None
    except TimeoutError:
        logger.info("Web page request timed out for %s", url)
        return None
    except (URLError, OSError) as exc:
        logger.info("Web page request failed for %s: %s", url, exc)
        return None

    html = _decode_response_body(body, content_type)
    return WebPageResponse(
        article_id="",
        url=url,
        final_url=final_url,
        content_type=content_type,
        html=html,
    )


def load_article_content(
    article_id: str,
    db_path: Path | str | None = None,
) -> ArticleContent | None:
    return get_article_content(article_id, db_path)


def save_cleaned_article_content(
    article_id: str,
    raw_html: str,
    cleaned_html: str,
    cleaned_markdown: str,
    plain_text: str,
    content_hash: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    save_article_content(
        article_id=article_id,
        raw_html=raw_html,
        cleaned_html=cleaned_html,
        cleaned_markdown=cleaned_markdown,
        plain_text=plain_text,
        content_hash=content_hash,
        db_path=db_path,
    )


# ── Private helpers ──────────────────────────────────────────────

def _should_fetch_reader_source(raw_html: str) -> bool:
    text = BeautifulSoup(raw_html or "", "lxml").get_text(separator="\n", strip=True)
    if not text:
        return True

    lower = text.lower()
    hnrss_markers = [
        "article url:",
        "comments url:",
        "points:",
        "# comments:",
    ]
    if sum(1 for marker in hnrss_markers if marker in lower) >= 2:
        return True

    return False

def _validate_web_url(url: str) -> str:
    value = url.strip()
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise HTTPException(status_code=409, detail="Article URL is not an absolute HTTP(S) URL")
    return value


def _decode_response_body(body: bytes, content_type: str | None) -> str:
    encoding = "utf-8"
    if content_type:
        for part in content_type.split(";"):
            key, _, value = part.strip().partition("=")
            if key.lower() == "charset" and value.strip():
                encoding = value.strip().strip('"')
                break
    try:
        return body.decode(encoding, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _inject_base_url(html: str, final_url: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    base = soup.new_tag("base", href=final_url)
    if soup.head:
        existing = soup.head.find("base")
        if existing:
            existing["href"] = final_url
        else:
            soup.head.insert(0, base)
    elif soup.html:
        head = soup.new_tag("head")
        head.append(base)
        soup.html.insert(0, head)
    else:
        return f'<base href="{final_url}">\n{html}'
    return str(soup)


def _extract_reader_candidate(soup: BeautifulSoup) -> BeautifulSoup:
    for selector in ("article", "main", "[role='main']"):
        candidate = soup.select_one(selector)
        if candidate is not None and candidate.get_text(strip=True):
            return BeautifulSoup(str(candidate), "lxml")

    for tag in soup.select("script, style, noscript, nav, header, footer, aside"):
        tag.decompose()
    return soup


def _count_words(text: str) -> int:
    """Count words in plain text by splitting on whitespace."""
    return len(text.split()) if text.strip() else 0


def _resolve_urls(soup: BeautifulSoup, source_url: str) -> None:
    """Convert relative URLs (href, src, etc.) to absolute using *source_url* as base."""
    for tag_name, attr_name in URL_ATTRS.items():
        for tag in soup.find_all(tag_name):
            value = tag.get(attr_name)
            if not value:
                continue
            # Only rewrite relative / protocol-relative URLs; leave absolutes and data URIs alone.
            if value.startswith(("http://", "https://", "mailto:", "data:", "#", "//")):
                continue
            tag[attr_name] = urljoin(source_url, value)


def _remove_tracking_pixels(soup: BeautifulSoup) -> None:
    """Remove <img> elements that look like tracking pixels."""
    for img in soup.find_all("img"):
        width = (img.get("width") or "").strip()
        height = (img.get("height") or "").strip()
        style = (img.get("style") or "").replace(" ", "").lower()

        # 1×1 pixel
        if width == "1" and height == "1":
            img.decompose()
            continue

        # Hidden via inline style
        if "display:none" in style or "visibility:hidden" in style:
            img.decompose()
            continue

        # Suspicious src path
        src = (img.get("src") or "").lower()
        if any(kw in src for kw in ["pixel", "tracking", "beacon", "1x1"]):
            img.decompose()
