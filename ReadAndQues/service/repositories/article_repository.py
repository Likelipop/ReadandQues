"""
service/repositories/article_repository.py — Canonical repository for article persistence and queries.
Protected by @db_safe error boundary.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.Mongo.article_index import (
    create_article_index,
    get_article_index,
    get_article_index_by_url,
    list_completed_articles,
)
from database.Mongo.exams import get_exam, get_exams_by_article_ids
from database.Minio.crud import read_bronze_meta, read_silver_clean
from service.domain.models import Article, Exam, Stage, Status
from service.repositories.utils import db_safe

logger = logging.getLogger(__name__)


def _safe_datetime(val):
    """Convert value to datetime or None. Discards unparseable string dates."""
    if val is None or isinstance(val, datetime):
        return val
    return None


def _build_article(index_doc: dict, exam_doc: Optional[dict] = None) -> Article:
    article_id = str(index_doc.get("_id", ""))
    exam_doc = exam_doc or {}

    stage_raw = index_doc.get("stage", "bronze")
    try:
        stage_enum = Stage(stage_raw)
    except ValueError:
        stage_enum = Stage.BRONZE

    status_raw = index_doc.get("ai_status", Status.PENDING.value)
    try:
        status_enum = Status(status_raw)
    except ValueError:
        status_enum = Status.PENDING

    exams = []
    for item in exam_doc.get("exams", []):
        if isinstance(item, dict):
            try:
                exams.append(Exam.model_validate(item))
            except Exception:
                pass

    return Article(
        article_id=article_id,
        id=article_id,
        url=index_doc.get("url", ""),
        title=index_doc.get("title", "No Title"),
        source_name=index_doc.get("source_name", "Unknown"),
        image_url=index_doc.get("image_url"),
        published_at=_safe_datetime(index_doc.get("published_at")),
        stage=stage_enum,
        status=status_enum,
        summary=exam_doc.get("summary", ""),
        theme=exam_doc.get("theme", "General"),
        genre=exam_doc.get("genre", "general"),
        exams=exams,
        error_message=index_doc.get("error_message", ""),
    )


class ArticleRepository:
    """Canonical repository for article persistence and queries."""

    @db_safe(default_return=None)
    def get_by_id(self, article_id: str) -> Optional[Article]:
        index_doc = get_article_index(article_id)
        if not index_doc:
            return None
        exam_doc = get_exam(article_id)
        return _build_article(index_doc, exam_doc)

    @db_safe(default_return=None)
    def get_by_url(self, url: str) -> Optional[Article]:
        index_doc = get_article_index_by_url(url)
        if not index_doc:
            return None
        exam_doc = get_exam(str(index_doc["_id"]))
        return _build_article(index_doc, exam_doc)

    @db_safe(default_return="")
    def save(self, article: Article) -> str:
        create_article_index(
            article_id=article.article_id,
            url=article.url,
            title=article.title,
        )
        return article.article_id

    @db_safe(default_return=False)
    def update(self, article_id: str, updates: dict) -> bool:
        from database.Mongo.connection import get_collection

        index_doc = get_article_index(article_id)
        if not index_doc:
            return False

        updates["updated_at"] = datetime.now(timezone.utc)
        result = get_collection("article_index").update_one(
            {"_id": article_id}, {"$set": updates}
        )
        return result.modified_count > 0

    @db_safe(default_return=[])
    def get_by_ids(self, ids: List[str]) -> List[Article]:
        if not ids:
            return []

        exam_map = get_exams_by_article_ids(ids)
        results = []
        for article_id in ids:
            index_doc = get_article_index(article_id)
            if index_doc:
                exam_doc = exam_map.get(article_id)
                results.append(_build_article(index_doc, exam_doc))
        return results

    @db_safe(default_return=None)
    def get_text_content(self, article_id: str) -> Optional[Dict[str, Any]]:
        silver_doc = read_silver_clean(article_id)
        if silver_doc:
            return {
                "original_text": silver_doc.get("original_text", ""),
                "cleaned_text": silver_doc.get("original_text", ""),
            }

        bronze_doc = read_bronze_meta(article_id)
        if bronze_doc:
            return {
                "original_text": bronze_doc.get("raw_text", ""),
                "cleaned_text": bronze_doc.get("raw_text", ""),
            }

        return None

    @db_safe(default_return=[])
    def list_completed(
        self,
        theme: Optional[str] = None,
        genre: Optional[str] = None,
        limit: int = 100,
    ) -> List[Article]:
        index_docs = list_completed_articles(limit=limit)
        if not index_docs:
            return []

        article_ids = [str(d["_id"]) for d in index_docs]
        exam_map = get_exams_by_article_ids(article_ids)

        results = []
        for index_doc in index_docs:
            article_id = str(index_doc["_id"])
            exam_doc = exam_map.get(article_id)

            if theme and exam_doc and exam_doc.get("theme") != theme:
                continue
            if genre and exam_doc and exam_doc.get("genre") != genre:
                continue

            results.append(_build_article(index_doc, exam_doc))

        return results

    @db_safe(default_return=None)
    def get_status_payload(self, article_id: str) -> Optional[Dict[str, Any]]:
        index_doc = get_article_index(article_id)
        if not index_doc:
            return None

        exam_doc = get_exam(article_id) or {}
        exams = exam_doc.get("exams", [])
        has_quiz = False
        if isinstance(exams, list) and len(exams) > 0:
            quizzes = exams[0].get("quizzes", []) if isinstance(exams[0], dict) else []
            if quizzes:
                has_quiz = True

        status = index_doc.get("ai_status", "pending")
        if has_quiz:
            quiz_status = "completed"
        elif status in ("pending", "processing", "failed"):
            quiz_status = status
        else:
            quiz_status = "none"

        return {
            "status": status,
            "has_quiz": has_quiz,
            "quiz_status": quiz_status,
            "message": index_doc.get("error_message", ""),
            "title": index_doc.get("title", ""),
            "exams": exams if has_quiz else [],
        }
