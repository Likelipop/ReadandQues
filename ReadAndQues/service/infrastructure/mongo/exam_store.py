"""
service/infrastructure/mongo/exam_store.py — Storage operations for the `exams` collection.
Handles saving, retrieving, and deleting generated IELTS/TOEFL exam documents.
"""

import logging
from datetime import UTC, datetime

from pymongo.errors import PyMongoError

from service.infrastructure.mongo.connection import get_collection

logger = logging.getLogger(__name__)


def _coll():
    return get_collection("exams")


def save_exam(article_id: str, exam_doc: dict) -> bool:
    """
    Upsert an exam document associated with an article_id.
    """
    exam_doc = {**exam_doc, "article_id": article_id, "updated_at": datetime.now(UTC)}
    created_at = exam_doc.pop("created_at", datetime.now(UTC))

    try:
        result = _coll().update_one(
            {"article_id": article_id},
            {"$set": exam_doc, "$setOnInsert": {"created_at": created_at}},
            upsert=True,
        )
        return bool(result.acknowledged)
    except PyMongoError as e:
        logger.error(f"MongoDB error in save_exam({article_id}): {e}")
        return False


def get_exam(article_id: str) -> dict | None:
    """
    Fetch the exam document for a specific article_id.
    """
    try:
        return _coll().find_one({"article_id": article_id})
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_exam({article_id}): {e}")
        return None


def list_exams(
    theme: str | None = None,
    genre: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    List exam documents filtered optionally by theme or genre.
    """
    query: dict = {}
    if theme:
        query["theme"] = theme
    if genre:
        query["genre"] = genre
    try:
        cursor = _coll().find(query).sort("created_at", -1).limit(limit)
        return list(cursor)
    except PyMongoError as e:
        logger.error(f"MongoDB error in list_exams: {e}")
        return []


def get_exams_by_article_ids(article_ids: list[str]) -> dict:
    """
    Batch fetch exam documents for a list of article_ids.
    Returns a dictionary mapping {article_id: exam_doc}.
    """
    if not article_ids:
        return {}
    try:
        cursor = _coll().find({"article_id": {"$in": article_ids}})
        return {doc["article_id"]: doc for doc in cursor if "article_id" in doc}
    except PyMongoError as e:
        logger.error(f"MongoDB error in get_exams_by_article_ids: {e}")
        return {}


def delete_exam(article_id: str) -> bool:
    """
    Delete exam document associated with the specified article_id.
    """
    try:
        res = _coll().delete_one({"article_id": article_id})
        return res.deleted_count > 0
    except PyMongoError as e:
        logger.error(f"MongoDB error in delete_exam({article_id}): {e}")
        return False
