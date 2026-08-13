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

from service.crawler.scraper import crawl_article_content
from service.repositories.search_repository import SearchRepository
from service.repositories.content_repository import ContentRepository
from service.repositories.pipeline_repository import PipelineRepository
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
    pipeline_repo = PipelineRepository()
    content_repo = ContentRepository()
    
    max_docs = kwargs.get("max_docs", 20)
    index_docs = pipeline_repo.list_by_stage(ArticleStage.SILVER, limit=max_docs)

    silver_items = []
    for index_doc in index_docs:
        article_id = index_doc["_id"]
        clean = content_repo.read_silver_clean(article_id)
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
    pipeline_repo = PipelineRepository()
    
    enriched_items = []

    for item in silver_items:
        article_id = item.get("article_id")
        original_text = item.get("original_text", "")

        if not original_text:
            logger.warning(f"[enrichment] No original_text for {article_id}, skipping.")
            continue

        pipeline_repo.update_ai_status(article_id, AIStatus.IN_PROGRESS)
        ai_result = _run_question_generator(original_text)

        if ai_result:
            enriched_items.append({**item, "ai_result": ai_result})
        else:
            pipeline_repo.update_ai_status(article_id, AIStatus.FAILED, "LangGraph pipeline failed")
            pipeline_repo.insert_log(
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
    pipeline_repo = PipelineRepository()
    content_repo = ContentRepository()
    search_repo = SearchRepository()
    
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
            content_repo.save_gold_enriched(article_id, gold_doc)

            # 2. MongoDB exams
            pipeline_repo.save_exam(article_id, gold_doc)

            # 3. article_index stage + ai_status
            pipeline_repo.update_article_stage(article_id, ArticleStage.GOLD)
            pipeline_repo.update_ai_status(article_id, AIStatus.COMPLETED)

            # 4. ChromaDB embedding
            summary = gold_doc["summary"] or gold_doc["title"]
            if summary:
                search_repo.index_article_vector(
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
            pipeline_repo.update_ai_status(article_id, AIStatus.FAILED, str(e))

    logger.info(f"[enrichment] save_to_gold done. Success: {success_count}/{len(enriched_items)}")
    return {"saved_gold": success_count}


@job("fetch_single_silver", inputs=["article_id"], outputs=["silver_items"])
def fetch_single_silver(article_id: str):
    """
    Atomic Job: Fetch a single silver clean doc by article_id from MinIO silver.
    Used by the AI-only re-run pipeline.
    """
    content_repo = ContentRepository()
    pipeline_repo = PipelineRepository()

    clean = content_repo.read_silver_clean(article_id)
    if not clean:
        logger.warning(f"[enrichment] Silver read failed for single article {article_id}")
        return {"silver_items": []}

    index_doc = pipeline_repo.get_article_index(article_id) or {}
    item = {**clean, "article_id": article_id, "_index": index_doc}
    logger.info(f"[enrichment] Fetched single silver item: {article_id}")
    return {"silver_items": [item]}


def process_single_article(article_id: str, url: str):
    """Legacy helper function for running single article pipeline."""
    from service.orchestration.pipes import single_article_pipe
    res = single_article_pipe.invoke(article_id=article_id, url=url)
    if res.get("status") == "completed":
        return {"status": "completed", "article_id": article_id}
    return {"status": "failed", "error": res.get("error", "Failed")}

