"""
service/crawler/pdf_parser.py — Scalable PDF paper & document extractor.

Extracts structured text, title, authors, section headers, and HTML layout
from academic papers and PDF URLs (e.g. arXiv, PubMed, open access papers).
"""

import io
import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from django.conf import settings
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def is_pdf_url_or_content(url: str, content_type: str) -> bool:
    """Check if the URL or HTTP Content-Type indicates a PDF file."""
    lowered_url = (url or "").lower().split("?")[0]
    lowered_ct = (content_type or "").lower()
    return (
        lowered_url.endswith(".pdf")
        or "application/pdf" in lowered_ct
        or "arxiv.org/pdf" in lowered_url
    )


def resolve_arxiv_pdf_url(url: str) -> Optional[str]:
    """
    If URL is an arXiv abstract page (e.g. https://arxiv.org/abs/2301.12345),
    convert it to the corresponding direct PDF URL.
    """
    match = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+(?:v\d+)?)", url, re.IGNORECASE)
    if match:
        arxiv_id = match.group(1)
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return None


def clean_pdf_text(raw_text: str) -> str:
    """Fix hyphenated line breaks, line wraps, and control characters in PDF text."""
    if not raw_text:
        return ""
    # Fix hyphenated words at line breaks: e.g. "com-\nmunication" -> "communication"
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", raw_text)
    # Replace single newlines inside paragraphs with a space while preserving double newlines
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    # Collapse multiple horizontal whitespace characters
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def parse_pdf_bytes(
    pdf_bytes: bytes,
    requested_url: str,
    final_url: str,
    http_status: int = 200,
) -> Dict[str, Any]:
    """
    Extract title, authors, markdown content, and HTML layout from raw PDF bytes.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        if num_pages == 0:
            raise ValueError("PDF file contains no pages.")
    except Exception as exc:
        logger.error(f"[PDF] Failed to parse PDF bytes from {final_url}: {exc}")
        raise ValueError("Could not read text from this PDF file.") from exc

    metadata = reader.metadata or {}
    pdf_title = (metadata.get("/Title") or getattr(metadata, "title", "") or "").strip()
    pdf_author = (metadata.get("/Author") or getattr(metadata, "author", "") or "").strip()

    # Extract text page by page
    page_texts: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            page_texts.append(text)

    if not page_texts:
        raise ValueError("No extractable text found in this PDF (might be scanned or image-only).")

    raw_combined = "\n\n".join(page_texts)
    cleaned_text = clean_pdf_text(raw_combined)

    # Derive Title if missing from metadata
    if not pdf_title or len(pdf_title) < 3 or pdf_title.lower().startswith("untitled"):
        first_page_lines = [line.strip() for line in page_texts[0].split("\n") if line.strip()]
        if first_page_lines:
            pdf_title = first_page_lines[0][:150]
        else:
            pdf_title = "Academic Paper"

    # Derive Source Name (e.g. arXiv, IEEE, PubMed, or domain)
    hostname = (urlparse(final_url).hostname or "Paper").removeprefix("www.")
    if "arxiv.org" in hostname:
        source_name = "arXiv Paper"
    elif "ncbi.nlm.nih.gov" in hostname or "pubmed" in hostname:
        source_name = "PubMed Paper"
    elif "sciencedirect" in hostname:
        source_name = "ScienceDirect"
    elif "nature.com" in hostname:
        source_name = "Nature"
    elif "plos.org" in hostname:
        source_name = "PLOS ONE"
    else:
        source_name = f"PDF ({hostname})"

    # Generate Markdown Content
    markdown_lines = [f"# {pdf_title}\n"]
    if pdf_author:
        markdown_lines.append(f"**Author(s):** {pdf_author}\n")

    markdown_lines.append(cleaned_text)
    markdown_content = "\n\n".join(markdown_lines)

    # Generate Standardized HTML Document for Reading Space UI
    soup = BeautifulSoup("<html><head></head><body><article></article></body></html>", "html.parser")
    wrapper = soup.article

    header_tag = soup.new_tag("header")
    title_tag = soup.new_tag("h1")
    title_tag.string = pdf_title
    header_tag.append(title_tag)

    if pdf_author:
        author_p = soup.new_tag("p")
        author_strong = soup.new_tag("strong")
        author_strong.string = "Author(s): "
        author_p.append(author_strong)
        author_p.append(pdf_author)
        header_tag.append(author_p)

    source_p = soup.new_tag("p")
    source_strong = soup.new_tag("strong")
    source_strong.string = "Source: "
    source_p.append(source_strong)
    source_link = soup.new_tag("a", href=final_url, target="_blank")
    source_link.string = final_url
    source_p.append(source_link)
    header_tag.append(source_p)

    wrapper.append(header_tag)

    # Body HTML
    body_div = soup.new_tag("div", attrs={"class": "article-body"})
    paragraphs = cleaned_text.split("\n\n")
    for para in paragraphs:
        p_str = para.strip()
        if p_str:
            p_tag = soup.new_tag("p")
            p_tag.string = p_str
            body_div.append(p_tag)

    wrapper.append(body_div)
    clean_html = str(soup)

    word_count = len(cleaned_text.split())

    # Check settings limits
    min_words = getattr(settings, "ARTICLE_MIN_WORDS", 100)
    max_words = getattr(settings, "ARTICLE_MAX_WORDS", 10000)

    if word_count < min_words:
        from service.crawler.scraper import CrawlError
        raise CrawlError(
            "CONTENT_TOO_SHORT",
            f"The paper needs at least {min_words} words to generate questions (found {word_count} words).",
        )

    if word_count > max_words:
        words = cleaned_text.split()[:max_words]
        cleaned_text = " ".join(words)
        word_count = len(words)

    return {
        "success": True,
        "url": requested_url,
        "canonical_url": final_url,
        "title": pdf_title,
        "raw_text": cleaned_text,
        "content": markdown_content,
        "html_content": clean_html,
        "source_name": source_name,
        "author": pdf_author or None,
        "published_at": datetime.now(timezone.utc),
        "language": "en",
        "word_count": word_count,
        "image_url": None,
        "image_urls": [],
        "crawl_metadata": {
            "crawler": "pypdf",
            "final_url": final_url,
            "http_status": http_status,
            "content_type": "application/pdf",
            "hostname": hostname,
            "pages": num_pages,
            "crawled_at": datetime.now(timezone.utc),
        },
    }
