import logging
from pipeline.etl.registry import job
from database.Mongo.crud import (
    get_unprocessed_bronze_docs,
    save_silver_doc,
    insert_pipeline_log
)
from pipeline.etl.config import BATCH_SIZE

logger = logging.getLogger(__name__)

@job("db_fetch_unprocessed_bronze", 
     inputs=["max_docs"], 
     outputs=["bronze_docs"])
def db_fetch_unprocessed_bronze(max_docs: int = BATCH_SIZE) -> list:
    logger.info(f"Fetching up to {max_docs} unprocessed bronze docs from DB...")
    return get_unprocessed_bronze_docs()[:max_docs]


@job("db_save_silver_batch", inputs=["silver_docs", "failed_bronze_logs"])
def db_save_silver_batch(silver_docs: list, failed_bronze_logs: list):
    logger.info(f"Saving {len(silver_docs)} silver docs and {len(failed_bronze_logs)} logs to DB...")
    
    success_count = 0
    # Save valid silver docs
    for doc in silver_docs:
        try:
            save_silver_doc(doc)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to save silver doc for {doc.get('bronze_id')}: {e}")
            
    # Save failed logs
    for log in failed_bronze_logs:
        insert_pipeline_log(**log)
        
    return {"saved": success_count, "failed_logs": len(failed_bronze_logs)}
