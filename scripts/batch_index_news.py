#!/usr/bin/env python3
"""
scripts/batch_index_news.py — Batch ETL script to index all MongoDB news into ChromaDB RAG store.
"""

import logging
import os
import sys

# Ensure ReadAndQues inner directory is on Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ReadAndQues"))

from database.Chroma.rag_operations import upsert_article_chunks
from database.Mongo.crud import (
    get_all_silver_articles_for_indexing,
    update_article_rag_indexed_status,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_index_news")


def main():
    logger.info("🚀 Starting batch indexing of MongoDB news articles into ChromaDB RAG store...")
    
    articles = get_all_silver_articles_for_indexing()
    total_articles = len(articles)
    logger.info(f"Found {total_articles} articles in MongoDB silver collection.")

    if total_articles == 0:
        logger.warning("No articles found in MongoDB to index.")
        return

    indexed_count = 0
    failed_count = 0

    for idx, article in enumerate(articles, 1):
        aid = article.get("article_id")
        title = article.get("title", "")
        text = article.get("full_text", "")
        url = article.get("url", "")
        theme = article.get("theme", "General")
        genre = article.get("genre", "general")
        published_at = article.get("published_at", "")

        if not text:
            logger.warning(f"[{idx}/{total_articles}] Skipping article {aid}: full_text is empty.")
            failed_count += 1
            continue

        success = upsert_article_chunks(
            article_id=aid,
            title=title,
            full_text=text,
            url=url,
            theme=theme,
            genre=genre,
            published_at=published_at,
        )

        if success:
            update_article_rag_indexed_status(aid, is_indexed=True)
            indexed_count += 1
            logger.info(f"[{idx}/{total_articles}] Successfully indexed article ID: {aid} ('{title[:40]}...')")
        else:
            failed_count += 1
            logger.error(f"[{idx}/{total_articles}] Failed to index article ID: {aid}")

    logger.info(
        f"\n✅ Batch Indexing Complete!\n"
        f"   - Total Processed: {total_articles}\n"
        f"   - Successfully Indexed: {indexed_count}\n"
        f"   - Failed/Skipped: {failed_count}\n"
    )


if __name__ == "__main__":
    main()
