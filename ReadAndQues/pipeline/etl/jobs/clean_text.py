import logging
from datetime import datetime, timezone
from pipeline.etl.jobs.clean_logic import clean_and_validate_article
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("logic_clean_batch", inputs=["bronze_docs"], outputs=["silver_docs", "failed_bronze_logs"])
def logic_clean_batch(bronze_docs: list):
    if not bronze_docs:
        logger.info("No bronze docs to clean.")
        return [], []

    silver_docs = []
    failed_logs = []

    for b_doc in bronze_docs:
        bronze_id = b_doc["_str_id"]
        url = b_doc.get("url")
        
        is_valid, error_msg, cleaned_data = clean_and_validate_article(b_doc)
        
        if not is_valid:
            logger.warning(f"Validation failed for {bronze_id} ({url}): {error_msg}")
            failed_logs.append({
                "stage": "silver",
                "status": "rejected",
                "message": error_msg,
                "document_id": bronze_id,
                "url": url,
            })
            continue
            
        silver_doc = {
            "bronze_id": bronze_id,
            "url": url,
            "title": cleaned_data.get("title", ""),
            "original_text": cleaned_data.get("original_text", ""),
            "source_name": cleaned_data.get("source_name", ""),
            "image_url": cleaned_data.get("image_url", ""),
            "word_count": cleaned_data.get("word_count", 0),
            "cleaned_at": datetime.now(timezone.utc),
        }
        silver_docs.append(silver_doc)
            
    logger.info(f"Logic clean batch finished. Success: {len(silver_docs)}/{len(bronze_docs)}")
    return silver_docs, failed_logs
