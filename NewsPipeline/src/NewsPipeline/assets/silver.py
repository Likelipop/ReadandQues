"""
NewsPipeline/assets/silver.py — Silver Assets: Fetch raw HTML and sanitize into clean structured articles.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

import trafilatura
from bs4 import BeautifulSoup
from dagster import Output, asset

from NewsPipeline.partitions import daily_partitions
from NewsPipeline.resources.minio_io_manager import MinIOResource

logger = logging.getLogger(__name__)

# Markers indicating the start of boilerplate footer/citation metadata
FOOTER_MARKERS = [
    "**Story Source:**",
    "Story Source:",
    "**Journal Reference:**",
    "Journal Reference:",
    "**Cite This Page:**",
    "Cite This Page:",
    "**Disclaimer:**",
    "Disclaimer:",
]

# Patterns for leading orphan metadata lines in science/news feeds
LEADING_METADATA_PATTERNS = [
    re.compile(r"^[-*•]?\s*Date:\s*$", re.IGNORECASE),
    re.compile(r"^[-*•]?\s*Source:\s*$", re.IGNORECASE),
    re.compile(r"^[-*•]?\s*Summary:\s*$", re.IGNORECASE),
    re.compile(r"^[-*•]?\s*Share:\s*$", re.IGNORECASE),
    re.compile(r"^[-*•]?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$", re.IGNORECASE),
]


def _extract_title_from_html(html_str: str, default_title: str = "Untitled") -> str:
    """Extract clean title from raw HTML with BeautifulSoup fallback."""
    if default_title and default_title != "Untitled":
        return default_title.strip()
    if not html_str:
        return default_title
    try:
        soup = BeautifulSoup(html_str, "html.parser")
        h1 = soup.find("h1")
        if h1 and h1.text and h1.text.strip():
            return h1.text.strip()
        if soup.title and soup.title.string:
            title_text = soup.title.string.strip()
            for sep in [" -- ", " - ", " | "]:
                if sep in title_text:
                    title_text = title_text.split(sep)[0].strip()
            return title_text
    except Exception:
        pass
    return default_title or "Untitled"


def _extract_image_url_from_html(html_str: str) -> str:
    """Extract lead/thumbnail image URL from raw HTML via OpenGraph / Twitter meta tags."""
    if not html_str:
        return ""
    try:
        soup = BeautifulSoup(html_str, "html.parser")
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og_img and og_img.get("content"):
            return str(og_img["content"]).strip()
        tw_img = soup.find("meta", attrs={"name": "twitter:image"}) or soup.find("meta", property="twitter:image")
        if tw_img and tw_img.get("content"):
            return str(tw_img["content"]).strip()
        link_img = soup.find("link", rel="image_src")
        if link_img and link_img.get("href"):
            return str(link_img["href"]).strip()
        art = soup.find("article") or soup.find("main")
        if art:
            img = art.find("img")
            if img and img.get("src") and str(img["src"]).startswith(("http://", "https://")):
                return str(img["src"]).strip()
    except Exception:
        pass
    return ""


def sanitize_article_text(raw_text: str) -> str:
    """
    Post-processing Sanitization Engine for extracted article Markdown text.
    1. Truncate boilerplate footers (**Story Source:**, **Journal Reference:**, etc.).
    2. Strip leading orphan metadata lines (- Date:, - Source:, - Summary:, - Share:).
    3. Normalize standalone bold subheadings into Markdown headers (### Subheading).
    4. Normalize paragraph breaks to clean double newlines (\n\n).
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text.strip()

    # 1. Truncate boilerplate footers (case-insensitive search)
    lower_text = text.lower()
    min_footer_idx = len(text)
    for marker in FOOTER_MARKERS:
        idx = lower_text.find(marker.lower())
        if idx != -1 and idx < min_footer_idx:
            min_footer_idx = idx
    text = text[:min_footer_idx].strip()

    # 2. Process lines for leading metadata and heading normalization
    raw_lines = text.split("\n")
    cleaned_lines: list[str] = []
    skip_next_value = False

    leading_prefixes = [
        "- date:", "date:",
        "- source:", "source:",
        "- summary:", "summary:",
        "- share:", "share:",
        "- story source:", "story source:",
    ]

    for i, line in enumerate(raw_lines):
        trimmed = line.strip()
        if not trimmed:
            cleaned_lines.append("")
            continue

        if i < 20:
            lowered = trimmed.lower()
            if any(lowered.startswith(p) for p in leading_prefixes):
                if lowered.startswith(("- date:", "date:", "- source:", "source:")):
                    parts = trimmed.split(":", 1)
                    if len(parts) > 1 and not parts[1].strip():
                        skip_next_value = True
                continue
            if skip_next_value:
                skip_next_value = False
                continue
            if re.match(r"^[-*•]?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$", trimmed, re.I):
                continue
            # Strip bullet prefix from summary if present
            if trimmed.startswith("- "):
                trimmed = trimmed[2:].strip()

        # 3. Standardize standalone bold lines into Markdown subheadings (### Subheading)
        bold_match = re.match(r"^\*\*([A-Za-z0-9\s,.\'\"!?:;—–-]+)\*\*\.?$", trimmed)
        if bold_match and len(trimmed) < 120 and not trimmed.endswith("."):
            subheading_title = bold_match.group(1).strip()
            cleaned_lines.append(f"### {subheading_title}")
        else:
            cleaned_lines.append(trimmed)

    # 4. Normalize paragraph breaks to clean double newlines
    combined = "\n".join(cleaned_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", combined).strip()

    return normalized


@asset(
    group_name="silver",
    partitions_def=daily_partitions,
    description="Download raw HTML for daily candidate articles and save to MinIO 'raw-html' bucket.",
)
def silver_raw_html(
    context,
    bronze_links: list[dict[str, Any]],
    minio_resource: MinIOResource,
) -> Output[list[dict[str, Any]]]:
    """
    Partitioned per day.
    Iterates through candidate links, downloads raw HTML via trafilatura,
    and saves byte-for-byte HTML to MinIO 'raw-html/<date>/<article_id>.html'.
    """
    target_date = context.partition_key
    downloaded_articles: list[dict[str, Any]] = []
    skipped_count = 0

    context.log.info(f"Silver Raw: Starting download for {len(bronze_links)} articles on {target_date}...")

    for item in bronze_links:
        url = item.get("url", "")
        article_id = item.get("article_id", "")
        title = item.get("title", "")

        if not url or not article_id:
            continue

        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                context.log.warning(f"Silver Raw: Could not download HTML from {url}")
                skipped_count += 1
                continue

            # Save raw HTML directly to MinIO 'raw-html' bucket
            minio_resource.save_html(target_date, article_id, downloaded)

            downloaded_articles.append(
                {
                    "article_id": article_id,
                    "url": url,
                    "title": title,
                    "source": item.get("source", ""),
                    "image_url": item.get("image_url", ""),
                    "published_at": item.get("published_at", ""),
                    "partition_date": target_date,
                }
            )
        except Exception as e:
            context.log.warning(f"Silver Raw: Error downloading {url}: {e}")
            skipped_count += 1

    context.log.info(
        f"Silver Raw: Successfully downloaded {len(downloaded_articles)}/{len(bronze_links)} HTML files for {target_date}."
    )

    return Output(
        value=downloaded_articles,
        metadata={
            "total_candidates": len(bronze_links),
            "downloaded_count": len(downloaded_articles),
            "skipped_count": skipped_count,
            "partition_date": target_date,
        },
    )


@asset(
    group_name="silver",
    partitions_def=daily_partitions,
    description="Sanitize raw HTML into clean structured articles and save to MinIO 'silver-cleaned' bucket.",
)
def silver_cleaned_articles(
    context,
    silver_raw_html: list[dict[str, Any]],
    minio_resource: MinIOResource,
) -> Output[list[dict[str, Any]]]:
    """
    Partitioned per day.
    Reads raw HTML from MinIO 'raw-html', extracts clean text via Trafilatura,
    applies Post-Processing Sanitization, validates quality gates,
    and persists structured clean JSON into MinIO 'silver-cleaned/<date>/<article_id>.json'.
    """
    target_date = context.partition_key
    clean_articles: list[dict[str, Any]] = []
    skipped_count = 0

    context.log.info(
        f"Silver Clean: Sanitizing and cleaning {len(silver_raw_html)} articles for {target_date}..."
    )

    for item in silver_raw_html:
        article_id = item["article_id"]
        try:
            raw_html = minio_resource.read_html(target_date, article_id)
            extracted_text = (
                trafilatura.extract(
                    raw_html,
                    output_format="markdown",
                    include_formatting=True,
                    include_links=True,
                    include_comments=False,
                )
                or ""
            )

            # Apply Post-Processing Sanitization Engine
            clean_text = sanitize_article_text(extracted_text)
            word_count = len(clean_text.split())

            # Quality gate: filter out stubs / short pages
            if word_count < 150:
                context.log.debug(
                    f"Silver Clean: Article '{item.get('title')}' skipped (clean word count {word_count} < 150)."
                )
                skipped_count += 1
                continue

            title = _extract_title_from_html(raw_html, default_title=item.get("title", "Untitled"))
            image_url = item.get("image_url") or _extract_image_url_from_html(raw_html) or ""

            doc = {
                "article_id": article_id,
                "url": item.get("url", ""),
                "title": title,
                "source": item.get("source", ""),
                "image_url": image_url,
                "thumbnail_url": image_url,
                "original_text": clean_text,
                "word_count": word_count,
                "published_at": item.get("published_at", ""),
                "partition_date": target_date,
                "sanitized_at": datetime.now(UTC).isoformat(),
            }

            # Save clean JSON to MinIO 'silver-cleaned' bucket
            minio_resource.save_silver_article(target_date, article_id, doc)
            clean_articles.append(doc)

        except Exception as e:
            context.log.warning(f"Silver Clean: Error processing article {article_id}: {e}")
            skipped_count += 1

    context.log.info(
        f"Silver Clean: Successfully sanitized and saved {len(clean_articles)} articles for {target_date}."
    )

    return Output(
        value=clean_articles,
        metadata={
            "sanitized_articles": len(clean_articles),
            "skipped_count": skipped_count,
            "partition_date": target_date,
        },
    )
