#!/usr/bin/env python3
"""
scripts/batch_index_news.py — Batch ETL script to index all MongoDB news into ChromaDB RAG store.
"""

import logging
import os
import sys

# Ensure ReadAndQues inner directory is on Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ReadAndQues"))

import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.mongo.article_store as article_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_index_news")


def main():
    logger.info("🚀 Starting batch indexing of MongoDB news articles into ChromaDB RAG store...")
    
    articles = article_store.list_completed_articles(limit=1000)
    total_articles = len(articles)
    logger.info(f"Found {total_articles} articles in MongoDB to index.")

    if total_articles == 0:
        logger.warning("No articles found in MongoDB to index.")
        return

    indexed_count = 0
    failed_count = 0

    for idx, article in enumerate(articles, 1):
        aid = str(article.get("_id") or article.get("article_id") or "")
        title = article.get("title", "")
        text = article.get("original_text") or article.get("cleaned_text") or article.get("raw_text", "")
        url = article.get("url", "")
        theme = article.get("theme", "General")
        genre = article.get("genre", "general")
        published_at = str(article.get("published_at", ""))

        if not text:
            logger.warning(f"[{idx}/{total_articles}] Skipping article {aid}: text is empty.")
            failed_count += 1
            continue

        try:
            vector_store.upsert_article_chunks(
                article_id=aid,
                title=title,
                full_text=text,
                url=url,
                theme=theme,
                genre=genre,
                published_at=published_at,
            )
            indexed_count += 1
            logger.info(f"[{idx}/{total_articles}] Successfully indexed article ID: {aid} ('{title[:40]}...')")
        except Exception as e:
            failed_count += 1
            logger.error(f"[{idx}/{total_articles}] Failed to index article ID: {aid}: {e}")

    logger.info(
        f"\n✅ Batch Indexing Complete!\n"
        f"   - Total Processed: {total_articles}\n"
        f"   - Successfully Indexed: {indexed_count}\n"
        f"   - Failed/Skipped: {failed_count}\n"
    )


if __name__ == "__main__":
    main()
