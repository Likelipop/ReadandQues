"""
database/Mongo/exams.py — CRUD for the `exams` collection.

Design:
  - article_id is the foreign key (string, indexed unique)
  - Stores AI-generated data: theme, genre, summary, analysis, exams list
  - Full gold data is also mirrored to MinIO gold/{article_id}/enriched.json
  - MongoDB serves fast reads for listing/filtering; MinIO is the source of truth
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from database.Mongo.connection import exams_collection

logger = logging.getLogger(__name__)


def save_exam(article_id: str, exam_doc: dict) -> bool:
    """
    Upsert an exam document by article_id.
    Safe to call multiple times — will replace existing data.
    """
    try:
        exam_doc = {**exam_doc, "article_id": article_id, "updated_at": datetime.now(timezone.utc)}
        exams_collection.update_one(
            {"article_id": article_id},
            {"$set": exam_doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"[exams] save failed for {article_id}: {e}")
        return False


def get_exam(article_id: str) -> Optional[dict]:
    """Fetch the exam document for a given article."""
    try:
        return exams_collection.find_one({"article_id": article_id})
    except Exception as e:
        logger.error(f"[exams] get failed for {article_id}: {e}")
        return None


def list_exams(
    theme: Optional[str] = None,
    genre: Optional[str] = None,
    limit: int = 100,
) -> List[dict]:
    """List exam documents with optional theme/genre filter."""
    query: dict = {}
    if theme:
        query["theme"] = theme
    if genre:
        query["genre"] = genre
    try:
        cursor = exams_collection.find(query).sort("created_at", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"[exams] list failed: {e}")
        return []


def get_exams_by_article_ids(article_ids: List[str]) -> dict:
    """
    Batch fetch exam documents for a list of article_ids.
    Returns a dict: {article_id: exam_doc}
    """
    if not article_ids:
        return {}
    try:
        cursor = exams_collection.find({"article_id": {"$in": article_ids}})
        return {doc["article_id"]: doc for doc in cursor}
    except Exception as e:
        logger.error(f"[exams] batch get failed: {e}")
        return {}
