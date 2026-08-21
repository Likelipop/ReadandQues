"""
service/services.py — Centralized Write Operations & Business Logic Services.
The SINGLE ENTRY POINT for all mutations. Views call these functions only.
"""

import logging
from typing import Any

import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.minio.object_store as object_store
import service.infrastructure.mongo.activity_store as activity_store
import service.infrastructure.mongo.article_store as article_store
import service.infrastructure.mongo.exam_store as exam_store
import service.infrastructure.mongo.pipeline_store as pipeline_store
from service.domain.contracts import generate_article_id
from service.domain.enums import AIStatus
from service.models import ExamAttemptLog, TopicProficiency
from service.pipelines import enrich_article_only, ingest_and_enrich_article
from service.tasks import run_in_background

logger = logging.getLogger(__name__)


def import_article(url: str, user_id: int) -> dict[str, Any]:
    """
    User submits a new article URL to import.
    Deduplicates against index; if new, triggers background ingestion pipeline.
    """
    existing = article_store.get_article_index_by_url(url)
    if existing:
        aid = str(existing["_id"])
        logger.info(f"Article URL already exists: {url} → {aid}")
        return {"status": "exists", "article_id": aid, "is_new": False}

    article_id = generate_article_id(url)
    article_store.create_article_index(article_id=article_id, url=url, stage="bronze", ai_status="pending")

    # Launch background ETL task
    run_in_background(ingest_and_enrich_article, article_id=article_id, url=url)

    return {"status": "created", "article_id": article_id, "is_new": True}


def trigger_quiz_generation(article_id: str) -> dict[str, Any]:
    """Re-trigger AI quiz generation for an existing silver article."""
    idx = article_store.get_article_index(article_id)
    if not idx:
        return {"status": "error", "message": "Article not found"}

    article_store.update_ai_status(article_id, AIStatus.PENDING_GENERATION)
    run_in_background(enrich_article_only, article_id=article_id)

    return {"status": "triggered", "article_id": article_id}


def submit_exam_attempt(
    user_id: int,
    article_id: str,
    score: int,
    total_questions: int,
    answers: dict,
    highlighted_markdown: str = "",
    elapsed_time: int = 0,
) -> dict[str, Any]:
    """Submit quiz results, save to PostgreSQL attempt log & TopicProficiency."""
    attempt_log = ExamAttemptLog.objects.create(
        user_id=user_id,
        article_id=article_id,
        score=score,
        total_questions=total_questions,
        answers=answers,
        highlighted_markdown=highlighted_markdown,
        elapsed_time=elapsed_time,
    )

    # Save activity session to MongoDB
    activity_store.log_reading_session(
        user_id=user_id,
        article_id=article_id,
        duration_sec=elapsed_time,
        completion_rate=1.0 if score > 0 else 0.5,
    )

    # Update Topic Proficiency for adaptive recommendation engine
    exam_doc = exam_store.get_exam(article_id) or {}
    topic = exam_doc.get("theme", "General")
    if user_id and topic:
        prof, _ = TopicProficiency.objects.get_or_create(user_id=user_id, topic=topic)
        prof.total_questions += total_questions
        prof.correct_answers += score
        prof.accuracy = prof.correct_answers / max(1, prof.total_questions)
        prof.save()

    return {
        "status": "success",
        "attempt_id": str(attempt_log.attempt_id),
        "score": score,
        "total_questions": total_questions,
    }


def run_daily_ingestion(max_articles: int = 10) -> dict[str, Any]:
    """Run daily RSS feed crawling & batch ingestion for Today's Brief."""
    from service.crawler.feed_crawler import fetch_rss_feed_links
    new_links = fetch_rss_feed_links(max_per_feed=5)
    unprocessed = pipeline_store.get_unprocessed_rss_links(limit=max_articles)

    processed_count = 0
    for item in unprocessed:
        url = item.get("link")
        if url:
            article_id = generate_article_id(url)
            article_store.create_article_index(article_id=article_id, url=url, stage="bronze", ai_status="pending")
            res = ingest_and_enrich_article(article_id=article_id, url=url)
            if res.get("status") == "completed":
                processed_count += 1
            pipeline_store.mark_rss_link_extracted(url)

    return {"status": "success", "crawled_count": len(new_links), "processed_count": processed_count}


def smart_paraphrase(
    article_id: str,
    paragraph_text: str,
    user_start_index: int = 0,
    user_end_index: int = 0,
    highlighted_text: str = "",
) -> dict[str, Any]:
    if not highlighted_text and paragraph_text and user_end_index > user_start_index:
        highlighted_text = paragraph_text[user_start_index:user_end_index]
    elif not highlighted_text:
        highlighted_text = paragraph_text

    import hashlib
    p_hash = hashlib.md5(f"{paragraph_text}:{highlighted_text}".encode()).hexdigest()

    cached = article_store.find_exact_paraphrase(
        article_id=article_id,
        paragraph_hash=p_hash,
        user_start_index=user_start_index,
        user_end_index=user_end_index,
    )
    if cached:
        return cached

    try:
        from service.ai_core.graphs.smart_paraphrase.graph import run_smart_paraphrase_flow
        result = run_smart_paraphrase_flow(
            highlighted_text=highlighted_text,
            paragraph_text=paragraph_text,
            start_idx=user_start_index,
            end_idx=user_end_index,
        )
        payload = {
            "article_id": article_id,
            "paragraph_hash": p_hash,
            "user_start_index": user_start_index,
            "user_end_index": user_end_index,
            "paraphrased_text": result.get("paraphrased_text", highlighted_text),
            "expanded_text": result.get("expanded_text", highlighted_text),
            "explanation": result.get("explanation", ""),
        }
        article_store.save_smart_paraphrase(dict(payload))
        return payload
    except Exception as e:
        logger.error(f"Smart paraphrase execution failed: {e}")
        return {
            "article_id": article_id,
            "paragraph_hash": p_hash,
            "paraphrased_text": highlighted_text,
            "expanded_text": highlighted_text,
            "explanation": f"Paraphrase service error: {str(e)}",
        }


def explain_phrase(
    article_id: str,
    phrase: str,
    paragraph_context: str = "",
) -> dict[str, Any]:
    """Execute the explained AI tool on a phrase within its paragraph context."""
    try:
        from service.ai_core.platform import get_ai_tool
        tool = get_ai_tool("explained")
        if tool:
            run_res = tool.run({
                "phrase": phrase,
                "paragraph_context": paragraph_context or phrase,
            })
            if run_res.status == "completed" and isinstance(run_res.output, dict):
                return {
                    "article_id": article_id,
                    "phrase": phrase,
                    "summary": run_res.output.get("summary", ""),
                    "detailed_explanation": run_res.output.get("detailed_explanation", ""),
                    "simplified_version": run_res.output.get("simplified_version", phrase),
                    "key_terms": run_res.output.get("key_terms", []),
                }
    except Exception as e:
        logger.error(f"Error using platform explained tool: {e}")

    try:
        from service.ai_core.graphs.explained import run_explained_flow
        res = run_explained_flow(phrase=phrase, paragraph_context=paragraph_context)
        return {
            "article_id": article_id,
            "phrase": phrase,
            "summary": res.get("summary", ""),
            "detailed_explanation": res.get("detailed_explanation", ""),
            "simplified_version": res.get("simplified_version", phrase),
            "key_terms": res.get("key_terms", []),
        }
    except Exception as e:
        logger.error(f"Error running explained flow: {e}")
        return {
            "article_id": article_id,
            "phrase": phrase,
            "summary": f"Contextual meaning of \"{phrase[:50]}\"",
            "detailed_explanation": f"In this passage, this phrase explains the core concept of {phrase}.",
            "simplified_version": phrase,
            "key_terms": [],
        }


def save_user_highlights(user_id: int, article_id: str, highlighted_text: str, note: str = "") -> bool:
    return activity_store.add_highlight(user_id=user_id, article_id=article_id, highlighted_text=highlighted_text, note=note)


def ask_rag_question(question: str, article_id: str | None = None) -> dict[str, Any]:
    try:
        from service.rag.router import execute_rag_pipeline
        res = execute_rag_pipeline(question=question, article_id=article_id)
        return res.model_dump(mode="json")
    except Exception as e:
        logger.error(f"RAG service query failed: {e}")
        return {"status": "error", "answer": f"Error executing RAG: {str(e)}", "citations": []}


def delete_article_hard(article_id: str) -> dict[str, Any]:
    article_store.delete_article(article_id)
    exam_store.delete_exam(article_id)
    activity_store.delete_article_activity(article_id)
    object_store.delete_article_objects(article_id)
    vector_store.delete_article_chunks(article_id)
    bm25_conn.rebuild_index()

    logger.info(f"🗑 Hard deleted article {article_id} across Mongo, MinIO, ChromaDB, and BM25")
    return {"status": "success", "article_id": article_id}
