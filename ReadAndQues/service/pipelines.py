"""
service/pipelines.py — Plain ETL Pipelines. Zero framework code.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import service.infrastructure.bm25.connection as bm25_conn
import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.minio.object_store as object_store
import service.infrastructure.mongo.article_store as article_store
import service.infrastructure.mongo.exam_store as exam_store
import service.infrastructure.mongo.pipeline_store as pipeline_store
from service.crawler.scraper import crawl_article_content
from service.domain.enums import AIStatus, ArticleStage

logger = logging.getLogger(__name__)


def _clean_and_validate(raw_doc: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    content = raw_doc.get("raw_text", "").strip()
    title = raw_doc.get("title", "").strip()
    source_name = raw_doc.get("source_name", "Unknown")

    if not content:
        return False, "Empty content after extraction", {}
    if not title:
        return False, "Missing title", {}

    cleaned_doc = {
        "title": title,
        "original_text": content,
        "html_content": raw_doc.get("html_content"),
        "source_name": source_name,
        "word_count": raw_doc.get("word_count") or len(content.split()),
        "canonical_url": raw_doc.get("canonical_url"),
        "author": raw_doc.get("author"),
        "published_at": raw_doc.get("published_at"),
        "language": raw_doc.get("language", "en"),
        "image_url": raw_doc.get("image_url"),
        "image_urls": raw_doc.get("image_urls") or [],
        "cleaned_at": datetime.now(UTC).isoformat(),
    }
    return True, "", cleaned_doc


def _run_ai_enrichment(text: str) -> dict | None:
    try:
        from service.ai_core.graphs import run_question_generator_flow

        final_state = run_question_generator_flow(text)
        return {
            "status": "completed",
            "analysis": final_state.get("semantic_analysis", {}),
            "exams": [final_state.get("final_exam", {})],
        }
    except Exception as e:
        logger.error(f"[pipelines] AI question generation failed: {e}")
        return None


def ingest_and_enrich_article(article_id: str, url: str) -> dict:
    """Full single-article pipeline: crawl → clean → silver → AI → gold."""
    logger.info(f"🚀 [Pipeline] Starting ingest_and_enrich_article: {article_id} ({url})")

    # Step 1: Crawl to Bronze
    crawl_res = crawl_article_content(url)
    if not crawl_res or not crawl_res.get("success"):
        err = crawl_res.get("error", "Crawl failed") if crawl_res else "Crawl failed"
        article_store.update_ai_status(article_id, AIStatus.FAILED, err)
        pipeline_store.insert_pipeline_log(stage="bronze", status="failed", message=err, url=url)
        return {"status": "failed", "error": err, "article_id": article_id}

    bronze_meta = {
        "article_id": article_id,
        "url": url,
        "title": crawl_res.get("title", ""),
        "source_name": crawl_res.get("source_name", "Unknown"),
        "image_url": crawl_res.get("image_url"),
        "image_urls": crawl_res.get("image_urls", []),
        "crawled_at": datetime.now(UTC).isoformat(),
        "raw_text": crawl_res.get("raw_text", ""),
        "html_content": crawl_res.get("html_content", ""),
        "word_count": crawl_res.get("word_count", 0),
        "language": crawl_res.get("language", "en"),
        "author": crawl_res.get("author", ""),
        "canonical_url": crawl_res.get("canonical_url", ""),
        "published_at": str(crawl_res.get("published_at") or ""),
    }

    object_store.save_bronze_html(article_id, crawl_res.get("html_content") or crawl_res.get("raw_text", ""))
    object_store.save_bronze_meta(article_id, bronze_meta)

    # Step 2: Validate & Save to Silver
    is_valid, err_msg, clean_doc = _clean_and_validate(bronze_meta)
    if not is_valid:
        article_store.update_ai_status(article_id, AIStatus.FAILED, err_msg)
        pipeline_store.insert_pipeline_log(stage="silver", status="failed", message=err_msg, url=url)
        return {"status": "failed", "error": err_msg, "article_id": article_id}

    object_store.save_silver_clean(article_id, clean_doc)
    article_store.update_article_stage(article_id, ArticleStage.SILVER)

    # Step 3: AI Enrichment
    article_store.update_ai_status(article_id, AIStatus.IN_PROGRESS)
    ai_result = _run_ai_enrichment(clean_doc["original_text"])

    if not ai_result:
        article_store.update_ai_status(article_id, AIStatus.FAILED, "AI generation failed")
        pipeline_store.insert_pipeline_log(stage="gold", status="failed", message="AI generation failed", url=url)
        return {"status": "failed", "error": "AI generation failed", "article_id": article_id}

    # Step 4: Save to Gold
    analysis = ai_result.get("analysis", {})
    exams_list = ai_result.get("exams", [])

    gold_doc = {
        "article_id": article_id,
        "url": url,
        "title": clean_doc["title"],
        "source_name": clean_doc["source_name"],
        "image_url": clean_doc.get("image_url"),
        "word_count": clean_doc.get("word_count", 0),
        "language": clean_doc.get("language", "en"),
        "theme": analysis.get("theme", "General"),
        "genre": analysis.get("genre", "general"),
        "summary": analysis.get("core", {}).get("summary", ""),
        "analysis": analysis,
        "exams": exams_list,
        "created_at": datetime.now(UTC).isoformat(),
    }

    object_store.save_gold_enriched(article_id, gold_doc)
    exam_store.save_exam(article_id, gold_doc)
    article_store.update_article_stage(article_id, ArticleStage.GOLD)
    article_store.update_ai_status(article_id, AIStatus.COMPLETED)

    # Index in ChromaDB & BM25
    summary = gold_doc["summary"] or gold_doc["title"]
    vector_store.add_article_vector(
        gold_id=article_id,
        summary=summary,
        title=gold_doc["title"],
        url=url,
        theme=gold_doc["theme"],
        genre=gold_doc["genre"],
    )
    vector_store.upsert_article_chunks(
        article_id=article_id,
        title=gold_doc["title"],
        full_text=clean_doc["original_text"],
        url=url,
        theme=gold_doc["theme"],
        genre=gold_doc["genre"],
    )

    # Rebuild BM25 search index asynchronously
    try:
        from service.tasks import task_rebuild_bm25_index

        task_rebuild_bm25_index.delay()
    except Exception:
        bm25_conn.rebuild_index()

    logger.info(f"✅ [Pipeline] Successfully finished ingest_and_enrich_article for {article_id}")
    return {"status": "completed", "article_id": article_id}


def enrich_article_only(article_id: str) -> dict:
    """Re-run AI enrichment on an existing silver article."""
    clean_doc = object_store.read_silver_clean(article_id)
    if not clean_doc:
        err = f"Silver document not found for {article_id}"
        article_store.update_ai_status(article_id, AIStatus.FAILED, err)
        return {"status": "failed", "error": err, "article_id": article_id}

    index_doc = article_store.get_article_index(article_id) or {}
    url = index_doc.get("url", "")

    article_store.update_ai_status(article_id, AIStatus.IN_PROGRESS)
    ai_result = _run_ai_enrichment(clean_doc["original_text"])

    if not ai_result:
        article_store.update_ai_status(article_id, AIStatus.FAILED, "AI enrichment failed")
        return {"status": "failed", "error": "AI enrichment failed", "article_id": article_id}

    analysis = ai_result.get("analysis", {})
    exams_list = ai_result.get("exams", [])

    gold_doc = {
        "article_id": article_id,
        "url": url,
        "title": clean_doc.get("title", ""),
        "source_name": clean_doc.get("source_name", ""),
        "image_url": clean_doc.get("image_url"),
        "word_count": clean_doc.get("word_count", 0),
        "language": clean_doc.get("language", "en"),
        "theme": analysis.get("theme", "General"),
        "genre": analysis.get("genre", "general"),
        "summary": analysis.get("core", {}).get("summary", ""),
        "analysis": analysis,
        "exams": exams_list,
        "created_at": datetime.now(UTC).isoformat(),
    }

    object_store.save_gold_enriched(article_id, gold_doc)
    exam_store.save_exam(article_id, gold_doc)
    article_store.update_article_stage(article_id, ArticleStage.GOLD)
    article_store.update_ai_status(article_id, AIStatus.COMPLETED)

    summary = gold_doc["summary"] or gold_doc["title"]
    vector_store.add_article_vector(
        gold_id=article_id,
        summary=summary,
        title=gold_doc["title"],
        url=url,
        theme=gold_doc["theme"],
        genre=gold_doc["genre"],
    )
    vector_store.upsert_article_chunks(
        article_id=article_id,
        title=gold_doc["title"],
        full_text=clean_doc["original_text"],
        url=url,
        theme=gold_doc["theme"],
        genre=gold_doc["genre"],
    )
    # Rebuild BM25 search index asynchronously
    try:
        from service.tasks import task_rebuild_bm25_index

        task_rebuild_bm25_index.delay()
    except Exception:
        bm25_conn.rebuild_index()

    return {"status": "completed", "article_id": article_id}
