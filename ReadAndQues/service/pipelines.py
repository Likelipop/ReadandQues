"""
service/pipelines.py — Ingestion and Quiz Generation Pipelines.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import trafilatura

from ai_service.interface import generate_quiz, index_article
from service.infrastructure.minio import object_store
from service.infrastructure.mongo import article_store, exam_store
from shared.enums import Stage as ArticleStage
from shared.enums import Status as AIStatus

logger = logging.getLogger(__name__)


def ingest_and_enrich_article(article_id: str, url: str) -> dict[str, Any]:
    """Single URL ingestion pipeline: fetch HTML -> extract -> AI quiz & keywords -> Gold."""
    logger.info(f"Starting ingest_and_enrich_article: {article_id} ({url})")

    # Step 1: Fetch HTML
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {"status": "failed", "error": "Fetch failed"}

        raw_text = (
            trafilatura.extract(
                downloaded,
                output_format="markdown",
                include_formatting=True,
                include_links=True,
                include_comments=False,
            )
            or ""
        )
        words = len(raw_text.split())
        if words < 50:
            return {"status": "failed", "error": "Content too short"}

        first_line = raw_text.split("\n")[0].strip() if raw_text else ""
        if first_line.startswith("#"):
            title = first_line.lstrip("#").strip()[:120]
        else:
            title = first_line[:120] if first_line else "Untitled Article"
    except Exception as e:
        logger.error(f"Crawling failed for {url}: {e}")
        return {"status": "failed", "error": str(e)}

    # Step 2: Save Silver Clean
    clean_doc = {
        "title": title,
        "original_text": raw_text,
        "html_content": downloaded if isinstance(downloaded, str) else "",
        "source_name": "Web Import",
        "word_count": words,
        "url": url,
        "cleaned_at": datetime.now(UTC).isoformat(),
    }
    object_store.save_silver_clean(article_id, clean_doc)

    # Step 3: AI Quiz & Keyword Generation
    try:
        ai_res = generate_quiz(raw_text)
    except Exception as e:
        logger.error(f"AI quiz generation failed for {article_id}: {e}")
        ai_res = {"keywords": ["General"], "summary": "", "questions": []}

    keywords = ai_res.get("keywords", ["General"])
    summary = ai_res.get("summary", "")
    quizzes = ai_res.get("questions", [])

    # Step 4: Save Gold Content & Exams
    gold_doc = {
        "article_id": article_id,
        "url": url,
        "title": title,
        "source": "Web Import",
        "original_text": raw_text,
        "word_count": words,
        "published_at": datetime.now(UTC).isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    article_store.save_gold_content(gold_doc)

    exam_doc = {
        "article_id": article_id,
        "keywords": keywords,
        "summary": summary,
        "exams": [{"quizzes": quizzes}],
        "created_at": datetime.now(UTC).isoformat(),
    }
    exam_store.save_exam(article_id, exam_doc)

    # Step 5: Index
    try:
        index_article(
            article_id=article_id,
            title=title,
            text=raw_text,
            url=url,
            keywords=keywords,
        )
    except Exception as e:
        logger.warning(f"Indexing failed for {article_id}: {e}")

    logger.info(f"Ingest and enrich completed successfully for {article_id}")
    return {"status": "completed", "article_id": article_id}


def enrich_article_only(article_id: str) -> dict[str, Any]:
    """Re-enrich an existing article with AI quiz generation."""
    clean_doc = object_store.read_silver_clean(article_id)
    if not clean_doc or not clean_doc.get("original_text"):
        article_store.update_ai_status(article_id, AIStatus.FAILED, error_message="No silver text found")
        return {"status": "failed", "error": "No silver text"}

    raw_text = clean_doc["original_text"]
    title = clean_doc.get("title", "Untitled")
    url = clean_doc.get("url", "")

    try:
        ai_res = generate_quiz(raw_text)
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        article_store.update_ai_status(article_id, AIStatus.FAILED, error_message=str(e))
        return {"status": "failed", "error": str(e)}

    keywords = ai_res.get("keywords", ["General"])
    summary = ai_res.get("summary", "")
    quizzes = ai_res.get("questions", [])

    exam_doc = {
        "article_id": article_id,
        "keywords": keywords,
        "summary": summary,
        "exams": [{"quizzes": quizzes}],
        "created_at": datetime.now(UTC).isoformat(),
    }
    exam_store.save_exam(article_id, exam_doc)
    article_store.update_article_stage(article_id, ArticleStage.GOLD.value)
    article_store.update_ai_status(article_id, AIStatus.COMPLETED)

    try:
        index_article(
            article_id=article_id,
            title=title,
            text=raw_text,
            url=url,
            keywords=keywords,
        )
    except Exception as e:
        logger.warning(f"Indexing failed for {article_id}: {e}")

    return {"status": "completed", "article_id": article_id}
