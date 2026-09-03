"""
service/selectors.py — Centralized Read Operations (Queries).

Provides pure Gold layer query functions without side effects:
- get_article_detail(article_id): 100% directly from MongoDB 'gold_content' & 'exams'.
- list_completed_articles(): paginated retrieval from 'gold_content'.
- get_hot_news(), get_recommendations(), get_related_articles().
- search_articles_keyword(): queries MinIO pre-computed BM25 index.
"""

import datetime
import logging
from typing import Any

from service.infrastructure.bm25.connection import get_index as get_bm25_index
from service.infrastructure.bm25.text_processing import process_text_to_tokens
from service.infrastructure.mongo import article_store, exam_store
from service.models import ExamAttemptLog
from shared.schemas import Article

logger = logging.getLogger(__name__)


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
    f = date_filter.lower().strip()
    if f in ("today", "24h", "1d"):
        return delta.total_seconds() <= 86400
    elif f in ("week", "past_week", "7d"):
        return delta.total_seconds() <= 7 * 86400
    elif f in ("month", "past_month", "30d"):
        return delta.total_seconds() <= 30 * 86400
    return True


def get_article_detail(article_id: str) -> dict[str, Any] | None:
    """
    Fetch complete article detail 100% from MongoDB 'gold_content' and 'exams'.
    Returns None if the article does not exist in 'gold_content'.
    """
    gold_doc = article_store.get_gold_content(article_id)
    if not gold_doc:
        return None

    original_text = gold_doc.get("original_text", "")
    title = gold_doc.get("title", "Untitled Article")
    source_name = gold_doc.get("source") or gold_doc.get("source_name") or "Academic News"
    url = gold_doc.get("url", "")
    word_count = gold_doc.get("word_count") or len(original_text.split())

    exam_doc = exam_store.get_exam(article_id) or {}
    exams_data = exam_doc.get("exams", [])
    analysis = exam_doc.get("analysis", {})

    keywords = exam_doc.get("keywords") or ["General"]
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    quizzes = exams_data[0].get("quizzes", []) if exams_data and isinstance(exams_data[0], dict) else []

    article_obj = Article(
        article_id=article_id,
        url=url,
        title=title,
        source_name=source_name,
        original_text=original_text,
        word_count=word_count,
        keywords=keywords,
        summary=exam_doc.get("summary") or analysis.get("core", {}).get("summary", ""),
        exams=exams_data,
        created_at=gold_doc.get("created_at") or datetime.datetime.now(datetime.UTC),
    )

    data = {
        "article_id": article_id,
        "id": article_id,
        "url": article_obj.url,
        "title": article_obj.title,
        "source_name": article_obj.source_name,
        "original_text": article_obj.original_text,
        "clean_text": article_obj.original_text,
        "word_count": article_obj.word_count,
        "keywords": article_obj.keywords,
        "summary": article_obj.summary,
        "exams": article_obj.exams,
        "quizzes": quizzes,
        "created_at": str(article_obj.created_at),
        "status": "completed",
        "stage": "gold",
        "has_quiz": bool(quizzes),
        "quiz_status": "completed" if quizzes else "pending",
    }
    return data


def get_article_status(article_id: str) -> dict[str, Any] | None:
    """Check article status directly from Gold content and exams."""
    gold_doc = article_store.get_gold_content(article_id)
    if not gold_doc:
        return None

    exam_doc = exam_store.get_exam(article_id)
    has_quiz = bool(exam_doc and exam_doc.get("exams"))

    return {
        "article_id": article_id,
        "stage": "gold",
        "ai_status": "completed",
        "status": "ready",
        "has_quiz": has_quiz,
        "error_message": "",
    }


def list_completed_articles(
    keyword: str | None = None,
    date_filter: str | None = None,
    query: str | None = None,
    page: int = 1,
    limit: int = 12,
    **kwargs,
) -> dict[str, Any]:
    """List Gold articles with keyword filtering, search, and pagination."""
    if query and query.strip():
        items = search_articles_keyword(query.strip(), limit=limit * 3)
    else:
        items = article_store.list_gold_articles(limit=200)

    all_items = []
    for doc in items:
        aid = str(doc.get("article_id") or doc.get("_id") or "")
        pub_at = doc.get("published_at")
        doc_kws = doc.get("keywords", [])
        if isinstance(doc_kws, str):
            doc_kws = [k.strip() for k in doc_kws.split(",") if k.strip()]
        if not doc_kws:
            doc_kws = ["General"]

        if keyword and keyword.lower() not in ("all", "all topics", ""):
            kw_match = any(keyword.lower() in k.lower() for k in doc_kws)
            if not kw_match:
                continue

        if not _is_within_date_filter(pub_at, date_filter):
            continue

        item = {
            "article_id": aid,
            "id": aid,
            "title": doc.get("title", "Untitled Article"),
            "source_name": doc.get("source") or doc.get("source_name", "Academic News"),
            "keywords": doc_kws,
            "theme": doc.get("theme", doc_kws[0] if doc_kws else "News"),
            "summary": doc.get("summary", ""),
            "original_text": doc.get("original_text", ""),
            "clean_text": doc.get("original_text", ""),
            "image_url": doc.get("image_url") or doc.get("thumbnail_url") or "",
            "word_count": doc.get("word_count", len(doc.get("original_text", "").split())),
            "published_at": str(pub_at) if pub_at else "",
            "has_quiz": True,
        }
        all_items.append(item)

    total_count = len(all_items)
    start = (page - 1) * limit
    end = start + limit
    paginated = all_items[start:end]

    return {
        "articles": paginated,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "has_next": end < total_count,
        "has_prev": page > 1,
    }


def get_popular_keywords(limit: int = 10) -> list[str]:
    """Return top unique keywords across all gold articles."""
    try:
        articles = article_store.list_gold_articles(limit=100)
    except Exception as e:
        logger.debug(f"Could not load articles for popular keywords ({e}), using default fallbacks.")
        articles = []

    seen: dict[str, int] = {}
    for doc in articles:
        kws = doc.get("keywords", [])
        if isinstance(kws, str):
            kws = [k.strip() for k in kws.split(",") if k.strip()]
        for kw in kws:
            clean = kw.strip()
            if clean and clean.lower() != "general":
                seen[clean] = seen.get(clean, 0) + 1

    sorted_kws = sorted(seen.keys(), key=lambda x: seen[x], reverse=True)
    return sorted_kws[:limit] if sorted_kws else ["Technology", "Science", "Education", "World", "Environment"]


def get_hot_news(limit: int = 3) -> list[dict[str, Any]]:
    """Spotlight / Breaking news articles for homepage carousel."""
    res = list_completed_articles(limit=limit)
    return res.get("articles", [])[:limit]


def get_recommendations(user=None, user_id=None, limit: int = 6) -> list[dict[str, Any]]:
    """Personalized recommendations based on recent articles."""
    res = list_completed_articles(limit=limit)
    return res.get("articles", [])[:limit]


def get_related_articles(article_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fetch related articles from Gold collection."""
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
    """Word of the Day payload."""
    return {
        "term": "mitigate",
        "phonetic": "/ˈmɪt.ɪ.ɡeɪt/",
        "part_of_speech": "verb",
        "definition": "To make something less harmful, severe, or painful.",
        "ielts_band": "Band 7.5+",
        "example_sentence": "Governments must take swift action to mitigate the economic impacts of climate change.",
        "collocations": ["mitigate risk", "mitigate the effects", "mitigate impact"],
        "synonyms": ["alleviate", "lessen", "reduce", "diminish"],
    }


def search_articles_keyword(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Search articles using pre-computed BM25 index from MinIO,
    fetching article details directly from MongoDB 'gold_content'.
    """
    raw_docs = []
    bm25_index, corpus_ids = get_bm25_index()
    if bm25_index and corpus_ids:
        query_tokens = process_text_to_tokens(query)
        if query_tokens:
            try:
                scores = bm25_index.get_scores(query_tokens)
                ranked_indices = sorted(
                    [i for i in range(len(corpus_ids)) if scores[i] > 0],
                    key=lambda i: scores[i],
                    reverse=True,
                )[:limit]
                matched_ids = [corpus_ids[i] for i in ranked_indices]
                for aid in matched_ids:
                    doc = article_store.get_gold_content(aid)
                    if doc:
                        raw_docs.append(doc)
            except Exception as e:
                logger.warning(f"BM25 search execution error: {e}")

    if not raw_docs:
        raw_docs = article_store.search_gold_content_by_text(query, limit=limit)

    results = []
    for doc in raw_docs:
        aid = str(doc.get("article_id") or doc.get("_id") or "")
        doc_kws = doc.get("keywords", [])
        if isinstance(doc_kws, str):
            doc_kws = [k.strip() for k in doc_kws.split(",") if k.strip()]
        if not doc_kws:
            doc_kws = ["General"]
        pub_at = doc.get("published_at")
        results.append({
            "article_id": aid,
            "id": aid,
            "title": doc.get("title", "Untitled Article"),
            "source_name": doc.get("source") or doc.get("source_name", "Academic News"),
            "keywords": doc_kws,
            "theme": doc.get("theme", doc_kws[0] if doc_kws else "News"),
            "summary": doc.get("summary", ""),
            "original_text": doc.get("original_text", ""),
            "clean_text": doc.get("original_text", ""),
            "image_url": doc.get("image_url") or doc.get("thumbnail_url") or "",
            "word_count": doc.get("word_count", len(doc.get("original_text", "").split())),
            "published_at": str(pub_at) if pub_at else "",
            "has_quiz": True,
        })
    return results


def search_articles_semantic(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Semantic vector search for articles against Gold ChromaDB collection."""
    try:
        from ai_service.interface import search_articles
        return search_articles(query=query, method="semantic", limit=limit)
    except Exception as e:
        logger.warning(f"Semantic search error: {e}")
        return []


def get_theme_choices() -> list[str]:
    """Return all available IELTS theme categories."""
    from shared.enums import ThemeCategory
    return [t.value for t in ThemeCategory]


def get_genre_choices() -> list[str]:
    """Return reading genre choices."""
    return ["Academic", "Journalistic", "Essay", "Report", "Interview", "General"]

