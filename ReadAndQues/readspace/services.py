"""
readspace/services.py — Application Services for Reading Space domain.
"""

from datetime import datetime, timezone
import logging

from service.domain.models import ExamAttempt, generate_article_id
from service.domain.enums import AIStatus, ArticleStage
from service.orchestrator import run_ai_only_pipeline_async, run_article_pipeline_async
from service.repositories import ArticleRepository, AttemptRepository
from service.repositories.search_repository import SearchRepository
from service.repositories.pipeline_repository import PipelineRepository

logger = logging.getLogger(__name__)


def get_article_detail(pk: str):
    repo = ArticleRepository()
    article = repo.get_by_id(pk)
    if not article:
        return None, []

    doc = article.model_dump(mode="json")
    doc["id"] = article.article_id
    # Determine quiz existence and quiz status
    exams = doc.get("exams", [])
    has_quiz = False
    if isinstance(exams, list) and len(exams) > 0:
        quizzes = exams[0].get("quizzes", []) if isinstance(exams[0], dict) else getattr(exams[0], "quizzes", [])
        if quizzes:
            has_quiz = True

    doc["has_quiz"] = has_quiz
    current_status = doc.get("status", "pending")
    if has_quiz:
        doc["quiz_status"] = "completed"
    elif current_status in ("pending", "processing", "failed"):
        doc["quiz_status"] = current_status
    else:
        doc["quiz_status"] = "none"

    doc["ai_status"] = doc["quiz_status"]

    # Fetch text content from repository
    text_content = repo.get_text_content(pk)
    if text_content:
        doc["original_text"] = text_content.get("original_text", "")
        doc["cleaned_text"] = text_content.get("cleaned_text", text_content.get("original_text", ""))
    else:
        doc["original_text"] = ""
        doc["cleaned_text"] = ""

    doc.setdefault("exams", [{"quizzes": []}])

    related_list = repo.list_completed(limit=6)
    related_articles = []
    for r in related_list:
        if r.article_id != article.article_id:
            r_dump = r.model_dump(mode="json")
            r_dump["id"] = r.article_id
            related_articles.append(r_dump)
    
    related_articles = related_articles[:5]

    return doc, related_articles


def import_article(url: str, user_id: int):
    """
    Import a new article. Uses article_index for dedup check.
    Creates article_index entry in BRONZE stage and triggers async pipeline.
    """
    pipeline_repo = PipelineRepository()
    
    # Dedup check — prefer new article_index
    existing = pipeline_repo.get_article_index_by_url(url)
    if existing and existing.get("ai_status") in (
        AIStatus.IN_PROGRESS.value,
        AIStatus.COMPLETED.value,
    ):
        return str(existing["_id"]), True

    # New article — create index entry and trigger pipeline
    article_id = generate_article_id(url)
    pipeline_repo.create_article_index(
        article_id=article_id,
        url=url,
        title="Loading title...",
    )

    run_article_pipeline_async(article_id, url)
    return article_id, False


def trigger_article_quiz(pk: str):
    article_repo = ArticleRepository()
    pipeline_repo = PipelineRepository()
    doc = article_repo.get_by_id(pk)
    if not doc:
        return False
    pipeline_repo.update_ai_status(pk, AIStatus.PENDING_GENERATION)
    run_ai_only_pipeline_async(pk)
    return True


def get_article_status_payload(pk: str):
    article_repo = ArticleRepository()
    payload = article_repo.get_status_payload(pk)
    return payload


def get_all_tests(theme: str = "All", genre: str = "All", user_id: int = None, search_query: str = None):
    article_repo = ArticleRepository()
    attempt_repo = AttemptRepository()

    if search_query and search_query.strip():
        from service.repositories.search_repository import SearchRepository
        search_repo = SearchRepository()
        hits = search_repo.search_keyword(search_query.strip(), limit=50) or []
        articles_list = []
        for h in hits:
            if h and hasattr(h, "article_id"):
                art = article_repo.get_by_id(h.article_id)
                if art:
                    a_dump = art.model_dump(mode="json")
                    a_dump["id"] = art.article_id
                    articles_list.append(a_dump)
    else:
        filtered_theme = theme if theme != "All" else None
        filtered_genre = genre if genre != "All" else None

        completed_articles = article_repo.list_completed(theme=filtered_theme, genre=filtered_genre, limit=100) or []
        articles_list = []
        for a in completed_articles:
            if a:
                a_dump = a.model_dump(mode="json")
                a_dump["id"] = a.article_id  # Ensure id is always present
                articles_list.append(a_dump)

    attempted_ids = attempt_repo.get_user_attempted_article_ids(user_id) if user_id else set()

    for art in articles_list:
        art_id = str(art.get("article_id") or art.get("id") or "")
        art["has_attempted"] = art_id in attempted_ids

    return articles_list


def save_attempt(model_data: dict, article_id: str, highlighted_markdown: str):
    attempt_repo = AttemptRepository()
    article_repo = ArticleRepository()

    attempt = ExamAttempt.model_validate(model_data)
    inserted_id = attempt_repo.save_attempt(attempt)

    related = []
    if highlighted_markdown:
        related_list = article_repo.list_completed(limit=6)
        for r in related_list:
            if r.article_id != article_id:
                r_dump = r.model_dump(mode="json")
                r_dump["id"] = r.article_id
                related.append(r_dump)
        related = related[:5]

    return inserted_id, related


def get_smart_paraphrase(pk: str, paragraph_hash: str, highlighted_text: str, paragraph_text: str, start_idx: int, end_idx: int):
    from service.orchestration.configuration import get_pipe
    pipe = get_pipe("smart_ink_pipe")
    pipe_result = pipe.invoke(
        article_id=pk,
        paragraph_hash=paragraph_hash,
        highlighted_text=highlighted_text,
        paragraph_text=paragraph_text,
        start_idx=start_idx,
        end_idx=end_idx,
    )
    return pipe_result.get("context", {}).get("paraphrase_data", {})


def search_bm25_articles(query: str):
    search_repo = SearchRepository()
    results = search_repo.search_keyword(query, limit=10) or []
    return [
        {
            "id": r.article_id,
            "title": r.title or "No Title",
            "source": r.source or "Unknown",
            "snippet": getattr(r, "snippet", "") or "",
            "date": r.date or "",
        }
        for r in results if r and hasattr(r, "article_id")
    ]


def search_semantic_articles(query: str):
    search_repo = SearchRepository()
    results = search_repo.search_semantic(query, limit=5) or []
    return [
        {
            "id": r.article_id,
            "title": r.title or "No Title",
            "source": r.source or "Unknown",
            "snippet": getattr(r, "snippet", "") or "",
            "date": r.date or "",
            "similarity": getattr(r, "similarity", None),
        }
        for r in results if r and hasattr(r, "article_id")
    ]
