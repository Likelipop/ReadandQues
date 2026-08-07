"""
service/repositories/article_repository.py

Canonical repository for article reads. Reads from:
  - article_index collection (metadata)
  - exams collection (AI results, theme, genre)

LegacyArticleReadAdapter is kept for any legacy ObjectId-based documents
still in the database during migration, and will be removed in Phase 8.
"""

import logging
from typing import List, Optional

from database.Mongo.article_index import (
    create_article_index,
    get_article_index,
    get_article_index_by_url,
    list_completed_articles,
)
from database.Mongo.exams import get_exam, get_exams_by_article_ids
from service.domain.contracts import ArticleContract, ExamContract, generate_article_id
from service.domain.enums import AIStatus, ArticleStatus

logger = logging.getLogger(__name__)


def _build_article_contract(index_doc: dict, exam_doc: Optional[dict] = None) -> ArticleContract:
    """Merge article_index + optional exam_doc into an ArticleContract."""
    article_id = str(index_doc.get("_id", ""))
    exam_doc = exam_doc or {}

    ai_status_raw = index_doc.get("ai_status", AIStatus.PENDING_GENERATION.value)
    try:
        ai_status_enum = AIStatus(ai_status_raw)
    except ValueError:
        ai_status_enum = AIStatus.PENDING_GENERATION

    # Map stage to ArticleStatus for backward compat with templates
    stage = index_doc.get("stage", "bronze")
    if ai_status_enum == AIStatus.COMPLETED:
        status_enum = ArticleStatus.COMPLETED
    elif ai_status_enum == AIStatus.FAILED:
        status_enum = ArticleStatus.FAILED
    elif stage in ("silver", "gold"):
        status_enum = ArticleStatus.PROCESSING
    else:
        status_enum = ArticleStatus.CRAWLING

    exams = []
    for item in exam_doc.get("exams", []):
        if isinstance(item, dict):
            try:
                exams.append(ExamContract.model_validate(item))
            except Exception:
                pass

    return ArticleContract(
        article_id=article_id,
        url=index_doc.get("url", ""),
        title=index_doc.get("title", "No Title"),
        original_text="",  # not stored in MongoDB — lives in MinIO silver
        cleaned_text="",
        summary=exam_doc.get("summary", ""),
        theme=exam_doc.get("theme", "General"),
        genre=exam_doc.get("genre", "general"),
        status=status_enum,
        ai_status=ai_status_enum,
        user_id=0,
        exams=exams,
        error_message=index_doc.get("error_message", ""),
    )


class ArticleRepository:
    """Canonical repository for article persistence and queries."""

    def get_by_id(self, article_id: str) -> Optional[ArticleContract]:
        index_doc = get_article_index(article_id)

        # Fallback to legacy collection for not-yet-migrated data
        if not index_doc:
            from bson import ObjectId
            from database.Mongo.connection import article_collection
            try:
                if ObjectId.is_valid(article_id):
                    legacy = article_collection.find_one({"_id": ObjectId(article_id)})
                    if legacy:
                        return self._adapt_legacy(legacy)
            except Exception as e:
                logger.error(f"[ArticleRepository] Legacy fallback failed for {article_id}: {e}")
            return None

        exam_doc = get_exam(article_id)
        return _build_article_contract(index_doc, exam_doc)

    def get_by_url(self, url: str) -> Optional[ArticleContract]:
        index_doc = get_article_index_by_url(url)
        if not index_doc:
            return None
        exam_doc = get_exam(str(index_doc["_id"]))
        return _build_article_contract(index_doc, exam_doc)

    def save(self, article: ArticleContract) -> str:
        create_article_index(
            article_id=article.article_id,
            url=article.url,
            title=article.title,
        )
        return article.article_id

    def list_completed(
        self,
        theme: Optional[str] = None,
        genre: Optional[str] = None,
        limit: int = 100,
    ) -> List[ArticleContract]:
        # Get completed index docs
        index_docs = list_completed_articles(theme=theme, genre=genre, limit=limit)
        if not index_docs:
            return []

        # Batch fetch exam docs
        article_ids = [str(d["_id"]) for d in index_docs]
        exam_map = get_exams_by_article_ids(article_ids)

        results = []
        for index_doc in index_docs:
            article_id = str(index_doc["_id"])
            exam_doc = exam_map.get(article_id)

            # Filter by theme/genre if provided (exams collection has these)
            if theme and exam_doc and exam_doc.get("theme") != theme:
                continue
            if genre and exam_doc and exam_doc.get("genre") != genre:
                continue

            results.append(_build_article_contract(index_doc, exam_doc))

        return results

    def _adapt_legacy(self, doc: dict) -> ArticleContract:
        """Minimal adapter for legacy gold_articles documents."""
        raw_id = str(doc.get("_id", ""))
        raw_status = doc.get("status", "crawling")
        try:
            status_enum = ArticleStatus(raw_status)
        except ValueError:
            status_enum = ArticleStatus.CRAWLING

        raw_ai = doc.get("ai_status", AIStatus.PENDING_GENERATION.value)
        try:
            ai_status_enum = AIStatus(raw_ai)
        except ValueError:
            ai_status_enum = AIStatus.PENDING_GENERATION

        exams = []
        for item in doc.get("exams", []):
            if isinstance(item, dict):
                try:
                    exams.append(ExamContract.model_validate(item))
                except Exception:
                    pass

        return ArticleContract(
            article_id=raw_id,
            url=doc.get("url", ""),
            title=doc.get("title", "No Title"),
            original_text=doc.get("original_text", ""),
            cleaned_text=doc.get("cleaned_text", ""),
            summary=doc.get("summary", ""),
            theme=doc.get("theme", "General"),
            genre=doc.get("genre", "general"),
            status=status_enum,
            ai_status=ai_status_enum,
            user_id=doc.get("user_id", 0),
            exams=exams,
            error_message=doc.get("error_message", ""),
        )
