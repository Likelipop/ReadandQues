"""
service/infrastructure/mongo/exam_store.py — Atomic I/O for the `exams` collection.
"""

from datetime import datetime, timezone
from typing import List, Optional
from service.infrastructure.mongo.connection import get_collection
from service.infrastructure.utils import db_safe


def _coll():
    return get_collection("exams")


@db_safe(default_return=False)
def save_exam(article_id: str, exam_doc: dict) -> bool:
    """Upsert an exam document by article_id."""
    exam_doc = {**exam_doc, "article_id": article_id, "updated_at": datetime.now(timezone.utc)}
    created_at = exam_doc.pop("created_at", datetime.now(timezone.utc))

    result = _coll().update_one(
        {"article_id": article_id},
        {"$set": exam_doc, "$setOnInsert": {"created_at": created_at}},
        upsert=True,
    )
    return result.acknowledged


@db_safe(default_return=None)
def get_exam(article_id: str) -> Optional[dict]:
    """Fetch the exam document for a given article."""
    return _coll().find_one({"article_id": article_id})


@db_safe(default_return=[])
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
    cursor = _coll().find(query).sort("created_at", -1).limit(limit)
    return list(cursor)


@db_safe(default_return={})
def get_exams_by_article_ids(article_ids: List[str]) -> dict:
    """Batch fetch exam documents for a list of article_ids."""
    if not article_ids:
        return {}
    cursor = _coll().find({"article_id": {"$in": article_ids}})
    return {doc["article_id"]: doc for doc in cursor}


@db_safe(default_return=False)
def delete_exam(article_id: str) -> bool:
    """Delete exam document by article_id."""
    res = _coll().delete_one({"article_id": article_id})
    return res.deleted_count > 0
