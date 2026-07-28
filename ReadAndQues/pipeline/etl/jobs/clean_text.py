import logging
from datetime import datetime, timezone

from articles.services.cleaning import clean_and_validate_article
from database.Mongo.crud import (get_unprocessed_bronze_docs,
                                 insert_pipeline_log, save_silver_doc)
from pipeline.etl.config import BATCH_SIZE
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("clean_text")
def clean_text(**kwargs):
    max_docs = kwargs.get("max_docs", BATCH_SIZE)
    bronze_docs = get_unprocessed_bronze_docs()[:max_docs]

    if not bronze_docs:
        logger.info("No unprocessed bronze docs found.")
        return {"processed": 0, "success": 0}

    success_count = 0
    for b_doc in bronze_docs:
        bronze_id = b_doc["_str_id"]
        url = b_doc.get("url")
        
        is_valid, error_msg, cleaned_data = clean_and_validate_article(b_doc)
        
        if not is_valid:
            logger.warning(f"Validation failed for {bronze_id} ({url}): {error_msg}")
            insert_pipeline_log(
                stage="silver",
                status="rejected",
                message=error_msg,
                document_id=bronze_id,
                url=url,
            )
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
        
        try:
            save_silver_doc(silver_doc)
            success_count += 1
            logger.info(f"Cleaned and saved to silver: {bronze_id}")
        except Exception as e:
            logger.error(f"Failed to save silver doc for {bronze_id}: {e}")
            
    logger.info(f"Clean text finished. Success: {success_count}/{len(bronze_docs)}")
    return {"processed": len(bronze_docs), "success": success_count}
