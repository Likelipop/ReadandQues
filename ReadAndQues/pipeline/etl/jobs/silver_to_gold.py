import logging
from datetime import datetime, timezone

from database.Mongo.crud import (
    get_unprocessed_silver_docs, 
    insert_gold_doc, 
    update_gold_doc
)
from database.Minio.crud import read_json_from_minio
from database.Minio.connection import SILVER_BUCKET
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)

@job("fetch_unprocessed_silver", outputs=["silver_docs"])
def fetch_unprocessed_silver(**kwargs):
    unprocessed_docs = get_unprocessed_silver_docs()
    
    # Enrich with full text from MinIO
    enriched_docs = []
    for doc in unprocessed_docs:
        minio_path = doc.get("minio_path")
        if minio_path:
            json_path = f"{minio_path}.json"
            full_data = read_json_from_minio(SILVER_BUCKET, json_path)
            if full_data:
                # Merge tracker and full data
                full_data["_str_id"] = str(doc.get("_id", ""))
                enriched_docs.append(full_data)
            else:
                logger.warning(f"Failed to read {json_path} from Silver MinIO")
                
    logger.info(f"Fetched {len(enriched_docs)} unprocessed silver documents.")
    return {"silver_docs": enriched_docs}


@job("transform_for_homepage", inputs=["silver_docs"], outputs=["homepage_docs"])
def transform_for_homepage(silver_docs: list):
    homepage_docs = []
    for doc in silver_docs:
        # Create a summary snippet for UI
        text = doc.get("original_text", "")
        summary = text[:200] + "..." if len(text) > 200 else text
        
        hp_doc = {
            "silver_id": doc.get("_str_id"),
            "article_id": doc.get("bronze_id"), # using bronze_id as the canonical article_id
            "title": doc.get("title"),
            "image_url": doc.get("image_url"), # Kept as image_url for UI compatibility
            "summary": summary,
            "category": doc.get("category", "General"),
            "published_at": doc.get("cleaned_at"), # Fallback to cleaned_at
            "source_name": doc.get("source_name"),
            "status": "active"
        }
        homepage_docs.append(hp_doc)
    
    logger.info(f"Transformed {len(homepage_docs)} docs for homepage.")
    return {"homepage_docs": homepage_docs}


@job("transform_for_ai", inputs=["silver_docs"], outputs=["ai_docs"])
def transform_for_ai(silver_docs: list):
    ai_docs = []
    for doc in silver_docs:
        ai_doc = {
            "silver_id": doc.get("_str_id"),
            "article_id": doc.get("bronze_id"),
            "full_text": doc.get("original_text"),
            "html_content": doc.get("html_content"), # Required for UI rendering
            "language": doc.get("language", "en"),
            "word_count": doc.get("word_count"),
            "ai_status": "pending_generation" # flag for AI pipelines
        }
        ai_docs.append(ai_doc)
        
    logger.info(f"Transformed {len(ai_docs)} docs for AI.")
    return {"ai_docs": ai_docs}


@job("save_to_gold_mongo", inputs=["homepage_docs", "ai_docs"])
def save_to_gold_mongo(homepage_docs: list, ai_docs: list):
    from database.Mongo.connection import db
    
    gold_homepage = db["gold_homepage_articles"]
    gold_ai = db["gold_ai_articles"]
    
    success_count = 0
    # Process paired lists
    for hp_doc, ai_doc in zip(homepage_docs, ai_docs):
        try:
            # We insert into gold_homepage_articles
            hp_res = gold_homepage.insert_one(hp_doc)
            
            # We insert into gold_ai_articles
            ai_res = gold_ai.insert_one(ai_doc)
            
            # Since get_unprocessed_silver_docs filters by `gold_collection.distinct("silver_id")` 
            # We need to make sure the original 'gold_articles' collection gets a dummy record or 
            # update crud.py to use `gold_homepage_articles` to check if a silver doc is processed.
            
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to save gold doc for article_id {hp_doc.get('article_id')}: {e}")
            
    return {"saved_gold": success_count}
