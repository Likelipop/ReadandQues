"""
worker_service/database/Crawler/scraper.py — Article web crawler.

Uses newspaper3k to extract article content and images.
"""

import logging
from urllib.parse import urlparse

from newspaper import Article as NewspaperArticle

from .formatter import to_markdown

logger = logging.getLogger(__name__)


def _extract_images(article: NewspaperArticle) -> tuple[str | None, list[str]]:
    """Extract valid image hotlink URLs from NewspaperArticle instance."""
    all_images = []
    top_image = article.top_image.strip() if article.top_image else None

    if top_image and not (
        top_image.startswith("http://") or top_image.startswith("https://")
    ):
        top_image = None

    raw_images = list(article.images) if article.images else []
    for img in raw_images:
        img_url = img.strip()
        if img_url.startswith("http://") or img_url.startswith("https://"):
            lower_url = img_url.lower()
            if not any(
                ext in lower_url for ext in [".svg", "pixel", "avatar", "sprite"]
            ):
                if img_url not in all_images:
                    all_images.append(img_url)

    if top_image:
        if top_image in all_images:
            all_images.remove(top_image)
        all_images.insert(0, top_image)
    elif all_images:
        top_image = all_images[0]

    return top_image, all_images


def crawl_article_content(url: str) -> dict:
    """
    Crawl a single article URL and return extracted data.

    Returns dict with keys: success, title, content, raw_text, source_name,
    image_url, image_urls, or success=False with error message.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        source_name = domain.replace("www.", "").strip() if domain else "Unknown"

        article = NewspaperArticle(url, keep_article_html=False)
        article.download()
        article.parse()

        if not article.text or not article.title:
            return {
                "success": False,
                "error": "Cannot extract content from this URL.",
            }

        raw_text = article.text.strip()
        formatted_content = to_markdown(raw_text)
        top_image, image_list = _extract_images(article)

        return {
            "success": True,
            "title": article.title.strip(),
            "content": formatted_content,
            "raw_text": raw_text,
            "source_name": source_name,
            "image_url": top_image,
            "image_urls": image_list,
        }

    except Exception as e:
        logger.error(f"Error crawling URL {url}: {str(e)}")
        return {
            "success": False,
            "error": f"Connection or parsing error: {str(e)}",
        }
