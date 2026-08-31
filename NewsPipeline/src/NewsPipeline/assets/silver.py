"""
NewsPipeline/assets/silver.py — Silver Asset: Fetch raw HTML for all articles in the daily partition.
"""

from typing import Any

import trafilatura
from dagster import Output, asset

from NewsPipeline.partitions import daily_partitions
from NewsPipeline.resources.minio_io_manager import MinIOResource


@asset(
    group_name="silver",
    partitions_def=daily_partitions,
    description="Download raw HTML for daily candidate articles, validate quality, and save to MinIO.",
)
def silver_raw_html(
    context,
    bronze_links: list[dict[str, Any]],
    minio_resource: MinIOResource,
) -> Output[list[dict[str, Any]]]:
    """
    Partitioned per day.
    Iterates through all candidate links for the day, downloads raw HTML via trafilatura,
    validates minimum word count, saves HTML files to MinIO 'raw-html/<date>/<article_id>.html',
    and passes downloaded article metadata to the gold layer.
    """
    target_date = context.partition_key
    downloaded_articles: list[dict[str, Any]] = []
    skipped_count = 0

    context.log.info(f"Silver: Starting download for {len(bronze_links)} articles on {target_date}...")

    for item in bronze_links:
        url = item.get("url", "")
        article_id = item.get("article_id", "")
        title = item.get("title", "")

        if not url or not article_id:
            continue

        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                context.log.warning(f"Silver: Could not download HTML from {url}")
                skipped_count += 1
                continue

            raw_text = trafilatura.extract(downloaded, include_comments=False) or ""
            word_count = len(raw_text.split())

            if word_count < 150:
                context.log.debug(f"Silver: Article '{title}' skipped (word count {word_count} < 150).")
                skipped_count += 1
                continue

            # Save HTML document to MinIO under date directory
            minio_resource.save_html(target_date, article_id, downloaded)

            downloaded_articles.append(
                {
                    "article_id": article_id,
                    "url": url,
                    "title": title,
                    "source": item.get("source", ""),
                    "published_at": item.get("published_at", ""),
                    "partition_date": target_date,
                    "word_count": word_count,
                }
            )
        except Exception as e:
            context.log.warning(f"Silver: Error processing {url}: {e}")
            skipped_count += 1

    context.log.info(
        f"Silver: Successfully saved {len(downloaded_articles)}/{len(bronze_links)} articles for {target_date}."
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
