"""
readspace/services.py — Application Services for Reading Space domain.
"""

from datetime import datetime, timezone
import logging

from database.BM25.operations import search_bm25
from database.BM25.text_preprocessing import process_text_to_tokens
from database.Chroma.operations import search_by_text
from database.Mongo.article_index import (
    create_article_index,
    get_article_index,
    get_article_index_by_url,
)
from database.Mongo.crud import (
    get_article_document_by_id,
    get_article_document_by_url,
    update_article_document,
)
from service.domain.contracts import ExamAttemptContract, generate_article_id
from service.domain.enums import AIStatus, ArticleStage
from service.orchestrator import run_ai_only_pipeline_async, run_article_pipeline_async
from service.repositories.article_repository import ArticleRepository
from service.repositories.attempt_repository import AttemptRepository

logger = logging.getLogger(__name__)


def get_article_detail(pk: str):
    repo = ArticleRepository()
    article = repo.get_by_id(pk)
    if not article:
        return None, []

    doc = article.model_dump(mode="json")
    doc["id"] = article.article_id

    doc.setdefault("exams", [{"quizzes": []}])

    related_list = repo.list_completed(limit=6)
    related_articles = [
        r.model_dump(mode="json") for r in related_list if r.article_id != article.article_id
    ][:5]

    return doc, related_articles


def import_article(url: str, user_id: int):
    """
    Import a new article. Uses article_index for dedup check.
    Creates article_index entry in BRONZE stage and triggers async pipeline.
    """
    # Dedup check — prefer new article_index
    existing = get_article_index_by_url(url)
    if existing and existing.get("ai_status") in (
        AIStatus.IN_PROGRESS.value,
        AIStatus.COMPLETED.value,
    ):
        return str(existing["_id"]), True

    # Fallback legacy check
    if not existing:
        legacy = get_article_document_by_url(url)
        if legacy and legacy.get("status") in ("crawling", "processing", "completed"):
            return str(legacy.get("id") or legacy.get("_id")), True

    # New article — create index entry and trigger pipeline
    article_id = generate_article_id(url)
    create_article_index(
        article_id=article_id,
        url=url,
        title="Loading title...",
    )

    run_article_pipeline_async(article_id, url)
    return article_id, False


def trigger_article_quiz(pk: str):
    doc = get_article_document_by_id(pk)
    if not doc:
        return False
    update_article_document(pk, {"ai_status": AIStatus.PENDING_GENERATION.value})
    run_ai_only_pipeline_async(pk)
    return True


def get_article_status_payload(pk: str):
    doc = get_article_document_by_id(pk)
    if not doc:
        return None

    status = doc.get("ai_status", doc.get("status", "pending"))
    payload = {
        "status": status,
        "message": doc.get("error_message", ""),
        "title": doc.get("title", ""),
    }

    if status == "completed":
        payload["exams"] = doc.get("exams", [])

    return payload


def get_all_tests(theme: str = "All", genre: str = "All", user_id: int = None):
    article_repo = ArticleRepository()
    attempt_repo = AttemptRepository()

    filtered_theme = theme if theme != "All" else None
    filtered_genre = genre if genre != "All" else None

    completed_articles = article_repo.list_completed(theme=filtered_theme, genre=filtered_genre, limit=100)
    articles_list = [a.model_dump(mode="json") for a in completed_articles]

    attempted_ids = attempt_repo.get_user_attempted_article_ids(user_id) if user_id else set()

    for art in articles_list:
        art_id = str(art.get("article_id") or art.get("id") or "")
        art["has_attempted"] = art_id in attempted_ids

    return articles_list


def save_attempt(model_data: dict, article_id: str, highlighted_markdown: str):
    attempt_repo = AttemptRepository()
    article_repo = ArticleRepository()

    contract = ExamAttemptContract.model_validate(model_data)
    inserted_id = attempt_repo.save_attempt(contract)

    related = []
    if highlighted_markdown:
        related_list = article_repo.list_completed(limit=6)
        related = [r.model_dump(mode="json") for r in related_list if r.article_id != article_id][:5]

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
    tokens = process_text_to_tokens(query)
    bm25_results = search_bm25(tokens, n=10)
    bm25_ids = [r["id"] for r in bm25_results]

    results = []
    for article_id in bm25_ids:
        try:
            doc = get_article_index(article_id)
            if doc:
                results.append({
                    "id": str(doc["_id"]),
                    "title": doc.get("title", "No Title"),
                    "source": doc.get("source_name", "Unknown"),
                    "snippet": "",  # title-based BM25 — no snippet
                    "date": doc.get("published_at", doc.get("created_at", "")).strftime("%Y-%m-%d")
                    if hasattr(doc.get("published_at", ""), "strftime") else "",
                })
        except Exception:
            continue
    return results


def search_semantic_articles(query: str):
    hits = search_by_text(query, limit=5)
    results = []
    for hit in hits:
        try:
            article_id = hit["id"]
            doc = get_article_index(article_id)
            if doc:
                distance = float(hit.get("distance", 0.0))
                similarity = max(0, min(100, int((1.0 - distance / 2.0) * 100)))
                metadata = hit.get("metadata", {})
                results.append({
                    "id": str(doc["_id"]),
                    "title": doc.get("title", metadata.get("title", "No Title")),
                    "source": doc.get("source_name", "Unknown"),
                    "snippet": "",
                    "date": doc.get("published_at", doc.get("created_at", "")).strftime("%Y-%m-%d")
                    if hasattr(doc.get("published_at", ""), "strftime") else "",
                    "similarity": similarity,
                })
        except Exception:
            continue
    return results
