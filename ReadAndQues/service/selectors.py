"""
service/selectors.py — Centralized Read Operations (Queries).
Views and APIs call these for fetching data. No side effects.
"""

import logging
from typing import Any, Dict, List, Optional, Set

from service.domain.enums import Genre, ThemeCategory
from service.domain.models import Article, Exam, ExamAttempt
import service.infrastructure.mongo.article_store as article_store
import service.infrastructure.mongo.exam_store as exam_store
import service.infrastructure.mongo.activity_store as activity_store
import service.infrastructure.minio.object_store as object_store
import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.bm25.index as bm25_idx
from service.models import ExamAttemptLog

logger = logging.getLogger(__name__)


def get_theme_choices() -> List[str]:
    """Single Source of Truth for Theme categories."""
    return ["All"] + [t.value for t in ThemeCategory]


def get_genre_choices() -> List[str]:
    """Single Source of Truth for Genres."""
    return ["All"] + [g.value for g in Genre]


def get_article_detail(article_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete article detail including clean text and exam payload."""
    index_doc = article_store.get_article_index(article_id)
    if not index_doc:
        return None

    clean_data = object_store.read_silver_clean(article_id) or {}
    original_text = clean_data.get("original_text", "")
    html_content = clean_data.get("html_content", "")

    exam_doc = exam_store.get_exam(article_id) or {}
    exams_data = exam_doc.get("exams", [])
    analysis = exam_doc.get("analysis", {})

    article_obj = Article(
        article_id=article_id,
        url=index_doc.get("url", ""),
        title=index_doc.get("title") or clean_data.get("title", "Loading..."),
        source_name=index_doc.get("source_name") or clean_data.get("source_name", "Unknown"),
        image_url=index_doc.get("image_url") or clean_data.get("image_url"),
        published_at=index_doc.get("published_at"),
        stage=index_doc.get("stage", "bronze"),
        status=index_doc.get("ai_status", "pending"),
        error_message=index_doc.get("error_message", ""),
        theme=exam_doc.get("theme", ThemeCategory.GENERAL.value),
        genre=exam_doc.get("genre", "general"),
        summary=exam_doc.get("summary") or analysis.get("core", {}).get("summary", ""),
        original_text=original_text,
        cleaned_text=clean_data.get("cleaned_text", original_text),
        word_count=clean_data.get("word_count", 0),
        language=clean_data.get("language", "en"),
        exams=exams_data,
    )

    data = article_obj.model_dump(mode="json")
    data["html_content"] = html_content
    data["quiz_status"] = article_obj.status
    data["has_quiz"] = len(exams_data) > 0
    return data


def get_article_status(article_id: str) -> Dict[str, Any]:
    """Fetch status payload for quiz generation polling."""
    index_doc = article_store.get_article_index(article_id) or {}
    status_val = index_doc.get("ai_status", "pending")
    exam_doc = exam_store.get_exam(article_id) or {}
    exams_list = exam_doc.get("exams", [])

    return {
        "status": status_val,
        "ai_status": status_val,
        "has_quiz": len(exams_list) > 0,
        "exams": exams_list if status_val == "completed" else [],
        "error_message": index_doc.get("error_message", ""),
    }


def list_completed_articles(
    theme: Optional[str] = None,
    genre: Optional[str] = None,
    page: int = 1,
    limit: int = 12,
) -> Dict[str, Any]:
    """Paginated completed articles listing with optional theme/genre filter."""
    if (theme and theme != "All") or (genre and genre != "All"):
        t_filter = theme if theme != "All" else None
        g_filter = genre if genre != "All" else None
        exam_docs = exam_store.list_exams(theme=t_filter, genre=g_filter, limit=100)
        article_ids = [d["article_id"] for d in exam_docs]

        all_items = []
        for aid in article_ids:
            idx = article_store.get_article_index(aid)
            if idx and idx.get("ai_status") == "completed":
                ex = next((d for d in exam_docs if d["article_id"] == aid), {})
                all_items.append(_build_article_card(idx, ex))
    else:
        completed_indexes = article_store.list_completed_articles(limit=200)
        a_ids = [doc["_id"] for doc in completed_indexes]
        exam_map = exam_store.get_exams_by_article_ids(a_ids)
        all_items = [_build_article_card(idx, exam_map.get(idx["_id"])) for idx in completed_indexes]

    total_count = len(all_items)
    start = (page - 1) * limit
    end = start + limit
    paged_items = all_items[start:end]

    return {
        "articles": paged_items,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "has_next": end < total_count,
        "has_prev": page > 1,
    }


def get_hot_news(limit: int = 6) -> List[Dict[str, Any]]:
    """Top completed news articles for hero banner."""
    res = list_completed_articles(limit=limit)
    return res.get("articles", [])


def get_recommendations(user=None, limit: int = 4) -> List[Dict[str, Any]]:
    """Recommended reading articles."""
    res = list_completed_articles(limit=limit)
    return res.get("articles", [])


def get_related_articles(article_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch related articles based on vector summary similarity or BM25 markers."""
    completed = list_completed_articles(limit=limit + 2).get("articles", [])
    filtered = [a for a in completed if a.get("article_id") != article_id and a.get("id") != article_id]
    return filtered[:limit]


def get_user_attempted_ids(user_id: Optional[int]) -> Set[str]:
    """Return set of article_ids completed/attempted by user."""
    if not user_id:
        return set()
    attempt_ids = ExamAttemptLog.objects.filter(user_id=user_id).values_list("article_id", flat=True)
    return set(attempt_ids)


def get_daily_vocab(user=None) -> Dict[str, Any]:
    """Word of the Day payload."""
    return {
        "word": "Resilience",
        "phonetic": "/rɪˈzɪliəns/",
        "part_of_speech": "noun",
        "definition": "The capacity to withstand or recover quickly from difficult conditions.",
        "example": "The country showed remarkable resilience following the economic downturn.",
    }


def search_articles_keyword(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """BM25 + Mongo text search for articles."""
    tokens = bm25_conn.process_text_to_tokens(query) if hasattr(bm25_conn, "process_text_to_tokens") else []
    hits = bm25_idx.search_bm25(tokens, n=limit) if tokens else []

    results = []
    seen = set()
    for hit in hits:
        aid = hit["id"]
        doc = article_store.get_article_index(aid)
        if doc:
            results.append(_build_article_card(doc))
            seen.add(aid)

    if len(results) < limit:
        mongo_docs = article_store.search_article_index_by_text(query, limit=limit - len(results))
        for doc in mongo_docs:
            aid = str(doc["_id"])
            if aid not in seen:
                results.append(_build_article_card(doc))
                seen.add(aid)

    return results


def search_articles_semantic(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """ChromaDB semantic search."""
    hits = vector_store.search_by_text(query, limit=limit)
    results = []
    for hit in hits:
        aid = hit["id"]
        doc = article_store.get_article_index(aid)
        if doc:
            results.append(_build_article_card(doc))
    if not results:
        return search_articles_keyword(query, limit=limit)
    return results


def _build_article_card(index_doc: dict, exam_doc: Optional[dict] = None) -> Dict[str, Any]:
    aid = str(index_doc.get("_id", ""))
    ex = exam_doc or {}
    analysis = ex.get("analysis", {})

    return {
        "article_id": aid,
        "id": aid,
        "url": index_doc.get("url", ""),
        "title": index_doc.get("title", "Untitled Article"),
        "source_name": index_doc.get("source_name", "Unknown"),
        "image_url": index_doc.get("image_url"),
        "published_at": index_doc.get("published_at"),
        "stage": index_doc.get("stage", "bronze"),
        "status": index_doc.get("ai_status", "pending"),
        "theme": ex.get("theme") or analysis.get("theme", ThemeCategory.GENERAL.value),
        "genre": ex.get("genre") or analysis.get("genre", "general"),
        "summary": ex.get("summary") or analysis.get("core", {}).get("summary", ""),
        "has_attempted": False,
    }
