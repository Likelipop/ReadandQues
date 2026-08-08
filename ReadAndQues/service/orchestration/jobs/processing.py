"""
service/orchestration/jobs/processing.py — Bronze → Silver processing jobs.

Jobs:
  fetch_unprocessed_bronze  — list bronze articles from article_index
  extract_bronze            — read bronze meta.json from MinIO
  validate_and_clean        — validate content and build clean silver doc
  save_to_silver            — save clean.json to MinIO silver + advance stage

Internal helpers (not @job):
  _clean_and_validate()     — pure function used by enrichment.py too
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from service.repositories.content_repository import ContentRepository
from service.repositories.pipeline_repository import PipelineRepository
from service.domain.enums import AIStatus, ArticleStage
from service.orchestration.configuration import job

logger = logging.getLogger(__name__)


# ── Internal helper (not a @job) ──────────────────────────────────────────────

def _clean_and_validate(raw_doc: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Pure function: validate and extract clean fields from a raw crawl result
    or bronze meta dict. Returns (is_valid, error_msg, cleaned_doc).
    Used by both the batch pipeline and process_single_article.
    """
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
        "cleaned_at": datetime.now(timezone.utc).isoformat(),
    }
    return True, "", cleaned_doc


# ── Pipeline Jobs ─────────────────────────────────────────────────────────────

@job("fetch_unprocessed_bronze", outputs=["bronze_ids"])
def fetch_unprocessed_bronze(**kwargs):
    """
    List article_ids currently at the BRONZE stage.
    Uses article_index stage flag — no distinct+$nin anti-pattern.
    """
    pipeline_repo = PipelineRepository()
    max_docs = kwargs.get("max_docs", 50)
    index_docs = pipeline_repo.list_by_stage(ArticleStage.BRONZE, limit=max_docs)
    bronze_ids = [doc["_id"] for doc in index_docs]
    logger.info(f"[processing] Found {len(bronze_ids)} unprocessed bronze articles.")
    return {"bronze_ids": bronze_ids}


@job("extract_bronze", inputs=["bronze_ids"], outputs=["bronze_docs"])
def extract_bronze(bronze_ids: list):
    """
    Read bronze meta.json from MinIO for each article_id.
    Skips articles where MinIO read fails (logs warning).
    """
    content_repo = ContentRepository()
    bronze_docs = []

    for article_id in bronze_ids:
        meta = content_repo.read_bronze_meta(article_id)
        if meta:
            meta["article_id"] = article_id
            bronze_docs.append(meta)
        else:
            logger.warning(f"[processing] Could not read bronze meta for {article_id}")

    logger.info(f"[processing] Extracted {len(bronze_docs)} bronze docs from MinIO.")
    return {"bronze_docs": bronze_docs}


@job("validate_and_clean", inputs=["bronze_docs"], outputs=["clean_docs", "rejected_logs"])
def validate_and_clean(bronze_docs: list):
    """
    Validate each bronze doc and build the clean silver structure.
    Merges the old validate_articles + clean_article_text steps.
    """
    clean_docs = []
    rejected_logs = []

    for doc in bronze_docs:
        article_id = doc.get("article_id", "")
        url = doc.get("url", "")

        is_valid, error_msg, cleaned = _clean_and_validate(doc)

        if is_valid:
            clean_docs.append({"article_id": article_id, "url": url, **cleaned})
        else:
            logger.warning(f"[processing] Rejected {article_id} ({url}): {error_msg}")
            rejected_logs.append({
                "stage": "silver_validate",
                "status": "rejected",
                "message": error_msg,
                "document_id": article_id,
                "url": url,
            })

    logger.info(
        f"[processing] Validation done. Valid: {len(clean_docs)}, Rejected: {len(rejected_logs)}"
    )
    return {"clean_docs": clean_docs, "rejected_logs": rejected_logs}


@job("save_to_silver", inputs=["clean_docs", "rejected_logs"], outputs=["saved_silver", "silver_items"])
def save_to_silver(clean_docs: list, rejected_logs: list):
    """
    Save each clean doc to MinIO silver/{article_id}/clean.json.
    Advance article_index stage to SILVER.
    Log all rejected docs to pipeline_logs.
    """
    pipeline_repo = PipelineRepository()
    content_repo = ContentRepository()
    success_count = 0

    for doc in clean_docs:
        article_id = doc.get("article_id")
        try:
            content_repo.save_silver_clean(article_id, doc)
            pipeline_repo.update_article_stage(article_id, ArticleStage.SILVER)
            success_count += 1
        except Exception as e:
            logger.error(f"[processing] Failed saving silver for {article_id}: {e}")

    for log in rejected_logs:
        pipeline_repo.insert_log(**log)
        # Mark rejected articles so they are not retried indefinitely
        doc_id = log.get("document_id")
        if doc_id:
            pipeline_repo.update_ai_status(doc_id, AIStatus.FAILED, log.get("message", "Validation rejected"))

    logger.info(f"[processing] Saved {success_count} silver docs. Logged {len(rejected_logs)} rejections.")
    return {"saved_silver": success_count, "failed_validation": len(rejected_logs), "silver_items": clean_docs}
