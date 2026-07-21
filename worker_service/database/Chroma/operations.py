"""
worker_service/database/Chroma/operations.py — ChromaDB operations.

Provides vector search and embedding indexing operations.
"""

import logging
from typing import Optional
from .connection import articles_collection

logger = logging.getLogger(__name__)


def add_article_vector(gold_id: str, summary: str, title: str, url: str) -> bool:
    """
    Insert or update an article summary embedding in ChromaDB vector store.
    """
    if not articles_collection or not summary:
        return False

    try:
        articles_collection.add(
            documents=[summary],
            metadatas=[{"title": title, "url": url}],
            ids=[str(gold_id)]
        )
        logger.info(f"Successfully added vector embedding for gold_id: {gold_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to add article vector to ChromaDB for gold_id {gold_id}: {e}")
        return False
