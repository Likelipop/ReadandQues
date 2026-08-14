from __future__ import annotations

import ipaddress
import logging
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from django.conf import settings
from lxml import html as lxml_html
from trafilatura import bare_extraction, fetch_response, extract
from trafilatura.settings import use_config
from bs4 import BeautifulSoup

import re
from .formatter import to_markdown

logger = logging.getLogger(__name__)

TRAFILATURA_CONFIG = use_config()
config_file = getattr(settings, "TRAFILATURA_CONFIG_FILE", None) if settings.configured else None
if config_file:
    TRAFILATURA_CONFIG.read(str(config_file))


class CrawlError(Exception):
    def __init__(self, code: str, public_message: str):
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


def _error(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "error": message, "error_code": code}


def _validate_public_http_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise CrawlError(
            "INVALID_URL", "URL must start with http:// or https://"
        )
    if not parsed.hostname:
        raise CrawlError("INVALID_URL", "URL does not have a valid domain")
    if parsed.username or parsed.password:
        raise CrawlError("INVALID_URL", "URL contains credentials!")
    try:
        address_info = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise CrawlError(
            "INVALID_URL", "Domain is invalid or does not exist"
        ) from exc

    for item in address_info:
        ip = ipaddress.ip_address(item[4][0])
        if any(
            (
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_reserved,
                ip.is_unspecified,
            )
        ):
            raise CrawlError(
                "PRIVATE_ADDRESS",
                "URL points to a restricted private network address.",
            )

def _parse_published_at(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            logger.info("Failed to parse published time")
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _first_src_from_srcset(srcset: str) -> str | None:
    first_candidate = srcset.split(",", 1)[0].strip()
    if not first_candidate:
        return None
    return first_candidate.split()[0]


# Normalize and filter out invalid or suspicious image URLs
def _normalize_image_url(raw_url: str | None, base_url: str) -> str | None:
    if not raw_url:
        return None
    normalized = urljoin(base_url, raw_url.strip())
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    lowered = normalized.lower()
    blocked_markers = (".svg", "sprite", "tracking", "pixel", "avatar")
    if any(marker in lowered for marker in blocked_markers):
        return None

    return normalized


# Extract images, prioritizing Open Graph and Twitter metadata
def _extract_images(
    html_content: bytes | str, base_url: str, limit: int
) -> tuple[str | None, list[str]]:
    try:
        tree = lxml_html.fromstring(html_content, base_url=base_url)
    except (ValueError, TypeError):
        return None, []
    candidates = []
    metadata_xpaths = (
        '//meta[@property="og:image"]/@content',
        '//meta[@property="og:image:secure_url"]/@content',
        '//meta[@name="twitter:image"]/@content',
        '//meta[@name="twitter:image:src"]/@content',
    )
    for xpath in metadata_xpaths:
        candidates.extend(tree.xpath(xpath))
        
    # Also extract images from the main article body
    for image in tree.xpath("//article//img | //main//img | //img"):
        raw_url = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-lazy-src")
            or _first_src_from_srcset(image.get("srcset", ""))
        )
        if raw_url:
            candidates.append(raw_url)
    image_urls: list[str] = []
    for candidate in candidates:
        normalized = _normalize_image_url(candidate, base_url)
        if normalized and normalized not in image_urls:
            image_urls.append(normalized)
        if len(image_urls) >= limit:
            break
    top_image = image_urls[0] if image_urls else None
    return top_image, image_urls


def _extract_article(
    html_content: bytes | str,
    requested_url: str,
    final_url: str,
    http_status: int,
    content_type: str,
) -> dict[str, Any]:
    document = bare_extraction(
        html_content,
        url=final_url,
        output_format="python",
        with_metadata=True,
        include_comments=False,
        include_tables=False,
        include_images=False,
        favor_precision=True,
        target_language="en",
        date_extraction_params={
            "extensive_search": True,
            "original_date": True,
        },
        config=TRAFILATURA_CONFIG,
    )

    if document is None:
        raise CrawlError(
            "EXTRACTION_FAILED",
            "Could not identify the main content of this article.",
        )
    extracted = document.as_dict()
    raw_text = (extracted.get("text") or getattr(document, "text", "") or "").strip()
    title = (extracted.get("title") or getattr(document, "title", "") or "").strip()

    if not raw_text or not title:
        raise CrawlError(
            "EXTRACTION_FAILED",
            "The article is missing a title or extractable content.",
        )

    content = to_markdown(raw_text)
    
    # Generate standardized HTML for UI rendering
    try:
        extracted_html = extract(
            html_content,
            url=final_url,
            output_format="html",
            include_images=True,
            include_links=True,
            config=TRAFILATURA_CONFIG,
        )
        if not extracted_html:
            extracted_html = f"<html><body><div><pre>{content}</pre></div></body></html>"
            
        published_date = _parse_published_at(extracted.get("date"))
        date_str = published_date.strftime("%B %d, %Y") if published_date else ""
        
        soup = BeautifulSoup(extracted_html, "html.parser")
        wrapper = BeautifulSoup("<html><head></head><body><article></article></body></html>", "html.parser")
        
        base_tag = wrapper.new_tag("base", href=final_url)
        wrapper.head.append(base_tag)
        
        header_tag = wrapper.new_tag("header")
        title_tag = wrapper.new_tag("h1")
        title_tag.string = title
        header_tag.append(title_tag)
        
        if date_str:
            date_tag = wrapper.new_tag("p")
            date_strong = wrapper.new_tag("strong")
            date_strong.string = "Published: "
            date_tag.append(date_strong)
            date_tag.append(date_str)
            header_tag.append(date_tag)
            
        if extracted.get("author"):
            author_tag = wrapper.new_tag("p")
            author_strong = wrapper.new_tag("strong")
            author_strong.string = "Author: "
            author_tag.append(author_strong)
            author_tag.append(extracted.get("author"))
            header_tag.append(author_tag)
            
        wrapper.article.append(header_tag)
        
        if soup.body:
            content_div = wrapper.new_tag("div", attrs={"class": "article-body"})
            for child in list(soup.body.children):
                content_div.append(child)
            wrapper.article.append(content_div)
            
        footer_tag = wrapper.new_tag("footer")
        footer_tag.append(wrapper.new_tag("hr"))
        link_p = wrapper.new_tag("p")
        link_p.string = "Source: "
        a_tag = wrapper.new_tag("a", href=final_url, target="_blank")
        a_tag.string = final_url
        link_p.append(a_tag)
        footer_tag.append(link_p)
        wrapper.article.append(footer_tag)
        
        clean_html = str(wrapper)
    except Exception as e:
        logger.error(f"Error generating standard HTML: {e}")
        clean_html = f"<html><body><h1>{title}</h1><div class='article-body'><pre>{content}</pre></div></body></html>"


    word_count = len(content.split())

    if word_count < settings.ARTICLE_MIN_WORDS:
        raise CrawlError(
            "CONTENT_TOO_SHORT",
            f"The article needs at least {settings.ARTICLE_MIN_WORDS} words to generate questions.",
        )

    if word_count > settings.ARTICLE_MAX_WORDS:
        raise CrawlError(
            "CONTENT_TOO_LARGE",
            "The article is too long to process in a single request.",
        )
    parsed_final_url = urlparse(final_url)
    fallback_source = (parsed_final_url.hostname or "Unknown").removeprefix("www.")
    source_name = (
        extracted.get("sitename") or extracted.get("hostname") or fallback_source
    )
    image_url, image_urls = _extract_images(
        html_content, base_url=final_url, limit=settings.ARTICLE_MAX_IMAGES
    )
    return {
        "success": True,
        "url": requested_url,
        "canonical_url": extracted.get("url") or final_url,
        "title": title,
        "raw_text": raw_text,
        "content": content,
        "html_content": clean_html,
        "source_name": str(source_name).strip(),
        "author": extracted.get("author"),
        "published_at": _parse_published_at(extracted.get("date")),
        "language": extracted.get("language") or "en",
        "word_count": word_count,
        "image_url": image_url,
        "image_urls": image_urls,
        "crawl_metadata": {
            "crawler": "trafilatura",
            "final_url": final_url,
            "http_status": http_status,
            "content_type": content_type,
            "hostname": extracted.get("hostname") or fallback_source,
            "fingerprint": extracted.get("fingerprint"),
            "crawled_at": datetime.now(timezone.utc),
        },
    }


def crawl_article_content(url: str) -> dict[str, Any]:
    requested_url = url.strip()
    try:
        from .pdf_parser import is_pdf_url_or_content, parse_pdf_bytes, resolve_arxiv_pdf_url

        target_url = resolve_arxiv_pdf_url(requested_url) or requested_url

        _validate_public_http_url(target_url)

        is_pdf_path = (target_url.lower().split("?")[0]).endswith(".pdf") or "arxiv.org/pdf" in target_url.lower()

        response = fetch_response(
            target_url,
            decode=not is_pdf_path,
            with_headers=True,
            config=TRAFILATURA_CONFIG,
        )  
        if response is None:
            raise CrawlError("DOWNLOAD_FAILED", "Could not download content from this URL.")
        status = int(response.status or 0)
        if status < 200 or status >= 300:
            raise CrawlError(
                "HTTP_ERROR",
                f"The website returned HTTP status {status}.",
            )
        if response.url:
            from urllib.parse import urljoin

            final_url = urljoin(target_url, response.url)
        else:
            final_url = target_url

        _validate_public_http_url(final_url)

        headers = response.headers or {}
        content_type = str(
            headers.get("content-type") or headers.get("Content-Type") or ""
        )

        # Handle PDF documents (arXiv, paper PDFs, direct PDF links)
        if is_pdf_url_or_content(final_url, content_type) or is_pdf_path:
            raw_pdf_bytes = getattr(response, "data", None)
            if not raw_pdf_bytes and hasattr(response, "html"):
                raw_pdf_bytes = response.html.encode("utf-8") if isinstance(response.html, str) else response.html

            if not raw_pdf_bytes:
                raise CrawlError("DOWNLOAD_FAILED", "PDF paper content was empty.")

            return parse_pdf_bytes(
                pdf_bytes=raw_pdf_bytes,
                requested_url=requested_url,
                final_url=final_url,
                http_status=status,
            )

        if content_type and not any(
            allowed in content_type.lower()
            for allowed in ("text/html", "application/xhtml+xml")
        ):
            raise CrawlError(
                "UNSUPPORTED_CONTENT",
                "The URL did not return an HTML page or PDF paper.",
            )
        html_content = response.html if response.html is not None else response.data
        if not html_content:
            raise CrawlError(
                "DOWNLOAD_FAILED",
                "The website returned empty content.",
            )

        return _extract_article(
            html_content=html_content,
            requested_url=requested_url,
            final_url=final_url,
            http_status=status,
            content_type=content_type,
        )
    except CrawlError as exc:
        logger.info(
            "Article rejected: code=%s url=%s message=%s",
            exc.code,
            requested_url,
            exc.public_message,
        )
        return _error(exc.code, exc.public_message)
    except Exception:
        logger.exception("Error while processing %s", requested_url)
        return _error(
            "UNEXPECTED_ERROR",
            "Could not process this article. Please try another URL.",
        )
