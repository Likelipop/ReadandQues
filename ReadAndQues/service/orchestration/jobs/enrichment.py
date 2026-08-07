"""
service/orchestration/jobs/enrichment.py — AI enrichment jobs (Silver → Gold).

Jobs:
  fetch_unprocessed_silver  — list silver articles from article_index
  run_ai_enrichment         — call LangGraph Question Generator on one article
  save_to_gold              — persist enriched data to MinIO gold + MongoDB exams
  process_single_article    — full pipeline for a single URL (crawl → clean → AI → gold)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from database.Chroma.operations import add_article_vector
from database.Crawler.scraper import crawl_article_content
from database.Minio.crud import (
    read_silver_clean,
    save_gold_enriched,
)
from database.Mongo.article_index import (
    list_by_stage,
    update_ai_status,
    update_article_stage,
    update_article_title,
)
from database.Mongo.crud import insert_pipeline_log
from database.Mongo.exams import save_exam
from service.ai_core.graphs.question_generator.graph import app as question_graph
from service.domain.contracts import generate_article_id, minio_bronze_prefix
from service.domain.enums import AIStatus, ArticleStage
from service.orchestration.configuration import job

logger = logging.getLogger(__name__)


# ── Internal helper ───────────────────────────────────────────────────────────

def _run_question_generator(text: str) -> dict | None:
    """Invoke LangGraph Question Generator and normalize output."""
    try:
        final_state = question_graph.invoke({"original_text": text})
        return {
            "status": "completed",
            "analysis": final_state.get("semantic_analysis", {}),
            "exams": [final_state.get("final_exam", {})],
        }
    except Exception as e:
        logger.error(f"[enrichment] LangGraph question generator failed: {e}")
        return None


# ── Pipeline Jobs ─────────────────────────────────────────────────────────────

@job("fetch_unprocessed_silver", outputs=["silver_items"])
def fetch_unprocessed_silver(**kwargs):
    """
    Fetch articles currently at the Silver stage.
    Each item: article_index doc + silver clean.json content merged.
    """
    max_docs = kwargs.get("max_docs", 20)
    index_docs = list_by_stage(ArticleStage.SILVER, limit=max_docs)

    silver_items = []
    for index_doc in index_docs:
        article_id = index_doc["_id"]
        clean = read_silver_clean(article_id)
        if clean:
            item = {**clean, "article_id": article_id, "_index": index_doc}
            silver_items.append(item)
        else:
            logger.warning(f"[enrichment] Silver MinIO read failed for {article_id}")

    logger.info(f"[enrichment] Fetched {len(silver_items)} silver articles.")
    return {"silver_items": silver_items}


@job("run_ai_enrichment", inputs=["silver_items"], outputs=["enriched_items"])
def run_ai_enrichment(silver_items: list):
    """Run LangGraph AI pipeline on each silver article."""
    enriched_items = []

    for item in silver_items:
        article_id = item.get("article_id")
        original_text = item.get("original_text", "")

        if not original_text:
            logger.warning(f"[enrichment] No original_text for {article_id}, skipping.")
            continue

        update_ai_status(article_id, AIStatus.IN_PROGRESS)
        ai_result = _run_question_generator(original_text)

        if ai_result:
            enriched_items.append({**item, "ai_result": ai_result})
        else:
            update_ai_status(article_id, AIStatus.FAILED, "LangGraph pipeline failed")
            insert_pipeline_log(
                stage="gold",
                status="failed",
                message="AI pipeline failed to generate exam",
                document_id=article_id,
                url=item.get("url"),
            )

    logger.info(f"[enrichment] AI enrichment done. Success: {len(enriched_items)}/{len(silver_items)}")
    return {"enriched_items": enriched_items}


@job("save_to_gold", inputs=["enriched_items"])
def save_to_gold(enriched_items: list):
    """
    Persist enriched data:
      1. MinIO gold/{article_id}/enriched.json
      2. MongoDB exams collection
      3. article_index stage → GOLD, ai_status → COMPLETED
      4. ChromaDB vector (summary embedding)
    """
    success_count = 0

    for item in enriched_items:
        article_id = item.get("article_id")
        ai_result = item.get("ai_result", {})
        analysis = ai_result.get("analysis", {})
        exams_list = ai_result.get("exams", [])

        gold_doc = {
            "article_id": article_id,
            "url": item.get("url", ""),
            "title": item.get("title", ""),
            "source_name": item.get("source_name", ""),
            "image_url": item.get("image_url"),
            "word_count": item.get("word_count", 0),
            "language": item.get("language", "en"),
            "theme": analysis.get("theme", "General"),
            "genre": analysis.get("genre", "general"),
            "summary": analysis.get("core", {}).get("summary", ""),
            "analysis": analysis,
            "exams": exams_list,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # 1. MinIO gold
            save_gold_enriched(article_id, gold_doc)

            # 2. MongoDB exams
            save_exam(article_id, gold_doc)

            # 3. article_index stage + ai_status
            update_article_stage(article_id, ArticleStage.GOLD)
            update_ai_status(article_id, AIStatus.COMPLETED)

            # 4. ChromaDB embedding
            summary = gold_doc["summary"] or gold_doc["title"]
            if summary:
                add_article_vector(
                    gold_id=article_id,
                    summary=summary,
                    title=gold_doc["title"],
                    url=gold_doc["url"],
                    theme=gold_doc["theme"],
                    genre=gold_doc["genre"],
                )

            success_count += 1
            logger.info(f"[enrichment] Saved gold for {article_id}")
        except Exception as e:
            logger.error(f"[enrichment] save_to_gold failed for {article_id}: {e}")
            update_ai_status(article_id, AIStatus.FAILED, str(e))

    logger.info(f"[enrichment] save_to_gold done. Success: {success_count}/{len(enriched_items)}")
    return {"saved_gold": success_count}


# ── On-Demand: Single Article Pipeline ───────────────────────────────────────

@job("process_single_article")
def process_single_article(**kwargs) -> Dict[str, Any]:
    """
    Full pipeline for a single user-submitted article:
      1. Crawl URL
      2. Clean & validate content
      3. Run LangGraph AI enrichment
      4. Save to MinIO gold + MongoDB exams + ChromaDB
    """
    from database.Minio.crud import save_bronze_html, save_bronze_meta, save_silver_clean
    from database.Mongo.article_index import create_article_index
    from service.orchestration.jobs.processing import _clean_and_validate

    article_id = kwargs.get("article_id")
    url = kwargs.get("url")

    if not article_id or not url:
        raise ValueError("process_single_article requires article_id and url")

    logger.info("🔄 [single] Starting pipeline for %s", article_id)

    # 1. Crawl
    crawl_result = crawl_article_content(url)
    if not crawl_result.get("success"):
        error_msg = crawl_result.get("error", "Crawl failed")
        update_ai_status(article_id, AIStatus.FAILED, error_msg)
        logger.error("❌ [single] Crawl failed for %s: %s", article_id, error_msg)
        return {"status": "failed", "article_id": article_id, "error": error_msg}

    # 2. Save Bronze
    save_bronze_html(article_id, crawl_result.get("html_content", ""))
    bronze_meta = {
        "url": url,
        "title": crawl_result.get("title", ""),
        "source_name": crawl_result.get("source_name", ""),
        "image_url": crawl_result.get("image_url"),
        "published_at": str(crawl_result.get("published_at") or ""),
        "raw_text": crawl_result.get("raw_text", ""),
        "word_count": crawl_result.get("word_count", 0),
        "language": crawl_result.get("language", "en"),
    }
    save_bronze_meta(article_id, bronze_meta)
    update_article_title(article_id, bronze_meta["title"])

    # 3. Clean & validate
    is_valid, error_msg, cleaned = _clean_and_validate(crawl_result)
    if not is_valid:
        update_ai_status(article_id, AIStatus.FAILED, error_msg)
        return {"status": "failed", "article_id": article_id, "error": error_msg}

    # 4. Save Silver
    save_silver_clean(article_id, cleaned)
    update_article_stage(article_id, ArticleStage.SILVER)
    update_ai_status(article_id, AIStatus.IN_PROGRESS)

    # 5. AI enrichment
    ai_result = _run_question_generator(cleaned.get("original_text", ""))
    if not ai_result:
        update_ai_status(article_id, AIStatus.FAILED, "AI pipeline failed")
        return {"status": "failed", "article_id": article_id, "error": "AI pipeline failed"}

    # 6. Save Gold
    analysis = ai_result.get("analysis", {})
    gold_doc = {
        "article_id": article_id,
        "url": url,
        "title": cleaned.get("title", ""),
        "source_name": cleaned.get("source_name", ""),
        "image_url": cleaned.get("image_url"),
        "word_count": cleaned.get("word_count", 0),
        "language": cleaned.get("language", "en"),
        "theme": analysis.get("theme", "General"),
        "genre": analysis.get("genre", "general"),
        "summary": analysis.get("core", {}).get("summary", ""),
        "analysis": analysis,
        "exams": ai_result.get("exams", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        save_gold_enriched(article_id, gold_doc)
        save_exam(article_id, gold_doc)
        update_article_stage(article_id, ArticleStage.GOLD)
        update_ai_status(article_id, AIStatus.COMPLETED)

        summary = gold_doc["summary"] or gold_doc["title"]
        if summary:
            add_article_vector(
                gold_id=article_id,
                summary=summary,
                title=gold_doc["title"],
                url=url,
                theme=gold_doc["theme"],
                genre=gold_doc["genre"],
            )

        logger.info("✅ [single] Pipeline completed for %s", article_id)
        return {"status": "completed", "article_id": article_id}
    except Exception as e:
        logger.exception("⚠️ [single] Failed saving gold for %s: %s", article_id, e)
        update_ai_status(article_id, AIStatus.FAILED, str(e))
        return {"status": "failed", "article_id": article_id, "error": str(e)}
