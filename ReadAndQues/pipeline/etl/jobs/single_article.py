import logging
from typing import Any, Dict

from pipeline.etl.jobs.clean_logic import clean_and_validate_article
from database.Chroma.operations import add_article_vector
from database.Crawler.scraper import crawl_article_content
from database.Mongo.crud import update_article_document
from pipeline.etl.jobs.generate_questions import run_ai_pipeline
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("process_single_article")
def process_single_article(**kwargs) -> Dict[str, Any]:
    """
    Executes the full pipeline for a single article in memory:
      1. Crawl URL
      2. Clean & Validate Content
      3. Update DB to 'processing'
      4. Run LangGraph AI Exam Generation Pipeline
      5. Save to MongoDB & ChromaDB
    """
    article_id = kwargs.get("article_id")
    url = kwargs.get("url")
    
    if not article_id or not url:
        raise ValueError("process_single_article requires article_id and url")
        
    logger.info("🔄 Starting single article pipeline for article_id=%s, url=%s", article_id, url)

    # 1. Crawl
    crawl_result = crawl_article_content(url)
    if not crawl_result.get("success"):
        error_msg = crawl_result.get("error", "Lỗi khi cào dữ liệu.")
        update_article_document(
            article_id,
            {
                "status": "failed",
                "error_message": error_msg,
            },
        )
        logger.error("❌ Crawl failed for article_id=%s: %s", article_id, error_msg)
        return {"status": "failed", "article_id": article_id, "error": error_msg}

    # 2. Clean & Validate
    is_valid, error_msg, cleaned_doc = clean_and_validate_article(crawl_result)
    if not is_valid:
        update_article_document(
            article_id, {"status": "failed", "error_message": error_msg}
        )
        logger.error("❌ Validation failed for article_id=%s: %s", article_id, error_msg)
        return {"status": "failed", "article_id": article_id, "error": error_msg}

    # 3. Update DB to 'processing'
    cleaned_doc["status"] = "processing"
    update_article_document(article_id, cleaned_doc)

    original_text = cleaned_doc.get("original_text", "")
    title = cleaned_doc.get("title", "")

    # 4. AI LangGraph Pipeline Execution
    ai_result = run_ai_pipeline(original_text)
    if ai_result:
        update_data = ai_result
        status_msg = "completed"
    else:
        update_data = {
            "status": "failed",
            "error_message": "AI pipeline failed to generate exam",
            "exams": [],
        }
        status_msg = "failed"

    try:
        update_article_document(article_id, update_data)
        if status_msg == "completed":
            summary = (
                ai_result.get("analysis", {}).get("core", {}).get("summary")
                or ai_result.get("analysis", {}).get("theme")
                or title
            )
            if summary:
                add_article_vector(
                    gold_id=article_id,
                    summary=summary,
                    title=title,
                    url=url,
                )
        logger.info("✅ Single pipeline task completed for article_id=%s, status=%s", article_id, status_msg)
        return {"status": status_msg, "article_id": article_id}
    except Exception as exc:
        logger.exception("⚠️ Failed updating article document for article_id=%s: %s", article_id, exc)
        return {"status": "failed", "article_id": article_id, "error": str(exc)}
