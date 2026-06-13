# from __future__ import annotations
#
# import asyncio
# from dataclasses import dataclass
# from urllib.error import HTTPError, URLError
# from urllib.parse import urlsplit
# from urllib.request import Request, urlopen
#
# from feed_engine.errors import FeedEngineError
#
#
# @dataclass(frozen=True)
# class FetchResponse:
#     status_code: int
#     final_url: str
#     body: bytes
#     etag: str | None
#     last_modified: str | None
#     content_type: str | None
#
#
# def validate_url(url: str) -> str:
#     value = url.strip()
#     parts = urlsplit(value)
#     if parts.scheme not in {"http", "https"} or not parts.netloc:
#         raise FeedEngineError(
#             "INVALID_URL",
#             "Feed URL must be an absolute http or https URL.",
#             status_code=400,
#             context={"url": url},
#         )
#     print("[VALIDATE URL]", repr(url))
#     return value
#
#
# async def fetch_feed(
#     url: str,
#     *,
#     etag: str | None = None,
#     last_modified: str | None = None,
#     timeout_seconds: float = 15.0,
# ) -> FetchResponse:
#     return await asyncio.to_thread(
#         _fetch_feed_sync,
#         validate_url(url),
#         etag,
#         last_modified,
#         timeout_seconds,
#     )
#
#
# def _fetch_feed_sync(
#     url: str,
#     etag: str | None,
#     last_modified: str | None,
#     timeout_seconds: float,
# ) -> FetchResponse:
#     headers = {
#         "User-Agent": "Mercury/0.1 feed-engine",
#         "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
#     }
#     if etag:
#         headers["If-None-Match"] = etag
#     if last_modified:
#         headers["If-Modified-Since"] = last_modified
#
#     request = Request(url, headers=headers)
#     try:
#         with urlopen(request, timeout=timeout_seconds) as response:
#             return FetchResponse(
#                 status_code=response.status,
#                 final_url=response.url,
#                 body=response.read(),
#                 etag=response.headers.get("ETag"),
#                 last_modified=response.headers.get("Last-Modified"),
#                 content_type=response.headers.get("Content-Type"),
#             )
#     except HTTPError as exc:
#         if exc.code == 304:
#             return FetchResponse(
#                 status_code=304,
#                 final_url=url,
#                 body=b"",
#                 etag=exc.headers.get("ETag"),
#                 last_modified=exc.headers.get("Last-Modified"),
#                 content_type=exc.headers.get("Content-Type"),
#             )
#         raise FeedEngineError(
#             "FETCH_FAILED",
#             "Feed server returned an error.",
#             status_code=502,
#             context={"url": url, "status": exc.code},
#         ) from exc
#     except TimeoutError as exc:
#         raise FeedEngineError(
#             "FETCH_TIMEOUT",
#             "Feed request timed out.",
#             status_code=504,
#             context={"url": url},
#         ) from exc
#     except (URLError, OSError) as exc:
#         raise FeedEngineError(
#             "FETCH_FAILED",
#             "Feed request failed.",
#             status_code=502,
#             context={"url": url, "reason": str(exc)},
#         ) from exc
from __future__ import annotations

import asyncio
import ssl
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from feed_engine.errors import FeedEngineError


@dataclass(frozen=True)
class FetchResponse:
    status_code: int
    final_url: str
    body: bytes
    etag: str | None
    last_modified: str | None
    content_type: str | None


def validate_url(url: str) -> str:
    value = url.strip()
    parts = urlsplit(value)

    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise FeedEngineError(
            "INVALID_URL",
            "Feed URL must be an absolute http or https URL.",
            status_code=400,
            context={"url": url},
        )

    print("[VALIDATE URL]", repr(url))
    return value


async def fetch_feed(
    url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    timeout_seconds: float = 15.0,
) -> FetchResponse:
    return await asyncio.to_thread(
        _fetch_feed_sync,
        validate_url(url),
        etag,
        last_modified,
        timeout_seconds,
    )


def _fetch_feed_sync(
    url: str,
    etag: str | None,
    last_modified: str | None,
    timeout_seconds: float,
) -> FetchResponse:

    headers = {
        "User-Agent": "Mercury/0.1 feed-engine",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }

    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    request = Request(url, headers=headers)

    print("[FETCH START]", url)

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            print("[FETCH OK]", response.status)

            return FetchResponse(
                status_code=response.status,
                final_url=response.url,
                body=response.read(),
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                content_type=response.headers.get("Content-Type"),
            )

    except HTTPError as exc:
        print("[HTTP ERROR]", exc.code, exc.reason)

        if exc.code == 304:
            return FetchResponse(
                status_code=304,
                final_url=url,
                body=b"",
                etag=exc.headers.get("ETag"),
                last_modified=exc.headers.get("Last-Modified"),
                content_type=exc.headers.get("Content-Type"),
            )

        raise FeedEngineError(
            "FETCH_FAILED",
            "Feed server returned HTTP error.",
            status_code=502,
            context={
                "url": url,
                "status": exc.code,
                "reason": str(exc.reason),
            },
        ) from exc

    except TimeoutError as exc:
        print("[TIMEOUT]", str(exc))

        raise FeedEngineError(
            "FETCH_TIMEOUT",
            "Feed request timed out.",
            status_code=504,
            context={"url": url},
        ) from exc

    except ssl.SSLCertVerificationError as exc:
        print("[SSL ERROR]", str(exc))

        raise FeedEngineError(
            "SSL_ERROR",
            "SSL certificate verification failed.",
            status_code=495,
            context={"url": url, "reason": str(exc)},
        ) from exc

    except URLError as exc:
        print("[URL ERROR]", repr(exc))

        raise FeedEngineError(
            "FETCH_FAILED",
            "Feed request failed (network error).",
            status_code=502,
            context={"url": url, "reason": str(exc)},
        ) from exc

    except OSError as exc:
        print("[OS ERROR]", str(exc))

        raise FeedEngineError(
            "FETCH_FAILED",
            "Feed request failed (OS error).",
            status_code=502,
            context={"url": url, "reason": str(exc)},
        ) from exc