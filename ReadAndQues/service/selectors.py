"""
service/selectors.py — Centralized Read Operations (Queries).
Views and APIs call these for fetching data. No side effects.
"""

import datetime
import logging
from typing import Any

import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.bm25.index as bm25_idx
import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.minio.object_store as object_store
import service.infrastructure.mongo.article_store as article_store
import service.infrastructure.mongo.exam_store as exam_store
from service.domain.enums import Genre, ThemeCategory
from service.domain.mock_data import DAILY_VOCAB_POOL, SAMPLE_ARTICLES
from service.domain.models import Article
from service.models import ExamAttemptLog

logger = logging.getLogger(__name__)


def get_theme_choices() -> list[str]:
    """Single Source of Truth for Theme categories."""
    return ["All"] + [t.value for t in ThemeCategory]


def get_genre_choices() -> list[str]:
    """Single Source of Truth for Genres."""
    return ["All"] + [g.value for g in Genre]


def _is_within_date_filter(published_at: Any, date_filter: str | None) -> bool:
    """Helper to check if published_at falls within specified date filter."""
    if not date_filter or date_filter.lower() in ("all", "all time", ""):
        return True
    if not published_at:
        return False

    dt = None
    if isinstance(published_at, datetime.datetime):
        dt = published_at
    elif isinstance(published_at, datetime.date):
        dt = datetime.datetime(published_at.year, published_at.month, published_at.day, tzinfo=datetime.UTC)
    elif isinstance(published_at, str):
        try:
            clean_str = published_at.strip().replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(clean_str)
        except Exception:
            return True

    if not dt:
        return True

    now = datetime.datetime.now(datetime.UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)

    delta = now - dt
    # Future dates are considered valid
    if delta.total_seconds() < 0:
        return True

    f = date_filter.lower().strip()
    if f in ("today", "24h", "1d"):
        return delta.total_seconds() <= 86400
    elif f in ("week", "past_week", "7d"):
        return delta.total_seconds() <= 7 * 86400
    elif f in ("month", "past_month", "30d"):
        return delta.total_seconds() <= 30 * 86400
    return True


def get_article_detail(article_id: str) -> dict[str, Any] | None:
    """Fetch complete article detail including clean text and exam payload."""
    # Check sample dataset fallback first
    for sample in SAMPLE_ARTICLES:
        if sample["article_id"] == article_id or sample["id"] == article_id:
            data = dict(sample)
            data["html_content"] = ""
            data["quiz_status"] = "completed"
            data["has_quiz"] = True
            return data

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


def get_article_status(article_id: str) -> dict[str, Any]:
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
    theme: str | None = None,
    genre: str | None = None,
    date_filter: str | None = None,
    page: int = 1,
    limit: int = 12,
) -> dict[str, Any]:
    """Paginated completed articles listing with optional theme/genre and publication date filters."""
    all_items = []
    if (theme and theme != "All") or (genre and genre != "All"):
        t_filter = theme if theme != "All" else None
        g_filter = genre if genre != "All" else None
        exam_docs = exam_store.list_exams(theme=t_filter, genre=g_filter, limit=100)
        article_ids = [d["article_id"] for d in exam_docs]

        for aid in article_ids:
            idx = article_store.get_article_index(aid)
            if idx and idx.get("ai_status") == "completed":
                ex = next((d for d in exam_docs if d["article_id"] == aid), {})
                card = _build_article_card(idx, ex)
                if _is_within_date_filter(card.get("published_at"), date_filter):
                    all_items.append(card)
    else:
        completed_indexes = article_store.list_completed_articles(limit=200)
        a_ids = [doc.get("_id") for doc in completed_indexes if isinstance(doc, dict)]
        exam_map = exam_store.get_exams_by_article_ids(a_ids)
        for idx in completed_indexes:
            if isinstance(idx, dict):
                card = _build_article_card(idx, exam_map.get(idx.get("_id")))
                if _is_within_date_filter(card.get("published_at"), date_filter):
                    all_items.append(card)

    if not all_items and SAMPLE_ARTICLES:
        all_items = [
            _build_article_card(
                {
                    "_id": a["article_id"],
                    "title": a["title"],
                    "source_name": a["source_name"],
                    "image_url": a["image_url"],
                    "published_at": a["published_at"],
                    "stage": a["stage"],
                    "ai_status": a["status"],
                },
                {
                    "theme": a["theme"],
                    "genre": a["genre"],
                    "summary": a["summary"],
                    "word_count": a["word_count"],
                },
            )
            for a in SAMPLE_ARTICLES
            if (not theme or theme == "All" or a["theme"].lower() == theme.lower())
            and (not genre or genre == "All" or a["genre"].lower() == genre.lower())
            and _is_within_date_filter(a.get("published_at"), date_filter)
        ]
        if not all_items and (not date_filter or date_filter.lower() in ("all", "all time")):
            all_items = [
                _build_article_card(
                    {
                        "_id": a["article_id"],
                        "title": a["title"],
                        "source_name": a["source_name"],
                        "image_url": a["image_url"],
                        "published_at": a["published_at"],
                        "stage": a["stage"],
                        "ai_status": a["status"],
                    },
                    {"theme": a["theme"], "genre": a["genre"], "summary": a["summary"], "word_count": a["word_count"]},
                )
                for a in SAMPLE_ARTICLES
            ]

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


def get_hot_news(limit: int = 6) -> list[dict[str, Any]]:
    """Top completed news articles for hero banner."""
    res = list_completed_articles(limit=limit)
    return res.get("articles", [])


def get_recommendations(user=None, limit: int = 4) -> list[dict[str, Any]]:
    """Adaptive recommendation engine based on user TopicProficiency."""
    user_id = getattr(user, "id", None) if user and getattr(user, "is_authenticated", False) else None
    if user_id:
        from service.models import TopicProficiency

        weak_topics = list(
            TopicProficiency.objects.filter(user_id=user_id, accuracy__lt=0.60).values_list("topic", flat=True)[:2]
        )
        if weak_topics:
            adapted = []
            for t in weak_topics:
                res = list_completed_articles(theme=t, limit=2)
                adapted.extend(res.get("articles", []))
            if adapted:
                return adapted[:limit]

    res = list_completed_articles(limit=limit)
    return res.get("articles", [])


def get_related_articles(article_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fetch related articles based on vector summary similarity or BM25 markers."""
    completed = list_completed_articles(limit=limit + 2).get("articles", [])
    filtered = [a for a in completed if a.get("article_id") != article_id and a.get("id") != article_id]
    return filtered[:limit]


def get_user_attempted_ids(user_id: int | None) -> set[str]:
    """Return set of article_ids completed/attempted by user."""
    if not user_id:
        return set()
    attempt_ids = ExamAttemptLog.objects.filter(user_id=user_id).values_list("article_id", flat=True)
    return set(attempt_ids)


def get_daily_vocab(user=None, user_id=None) -> dict[str, Any]:
    """Word of the Day payload deterministically selected per calendar day."""
    today_ordinal = datetime.date.today().toordinal()
    idx = today_ordinal % len(DAILY_VOCAB_POOL)
    return dict(DAILY_VOCAB_POOL[idx])


def search_articles_keyword(query: str, limit: int = 10) -> list[dict[str, Any]]:
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
            aid = str(doc.get("_id", ""))
            if aid and aid not in seen:
                results.append(_build_article_card(doc))
                seen.add(aid)

    if not results and SAMPLE_ARTICLES:
        q = query.lower()
        for a in SAMPLE_ARTICLES:
            if q in a["title"].lower() or q in a["summary"].lower() or q in a["theme"].lower():
                results.append(
                    _build_article_card(
                        {
                            "_id": a["article_id"],
                            "title": a["title"],
                            "source_name": a["source_name"],
                            "image_url": a["image_url"],
                            "published_at": a["published_at"],
                            "stage": a["stage"],
                            "ai_status": a["status"],
                        },
                        {
                            "theme": a["theme"],
                            "genre": a["genre"],
                            "summary": a["summary"],
                            "word_count": a["word_count"],
                        },
                    )
                )

    return results


def search_articles_semantic(query: str, limit: int = 5) -> list[dict[str, Any]]:
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


def _build_article_card(index_doc: dict, exam_doc: dict | None = None) -> dict[str, Any]:
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
        "original_text": ex.get("summary") or analysis.get("core", {}).get("summary", ""),
        "word_count": ex.get("word_count", 0),
        "has_attempted": False,
    }
