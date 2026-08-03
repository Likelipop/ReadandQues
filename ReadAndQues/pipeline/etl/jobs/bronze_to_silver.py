import logging
from datetime import datetime, timezone
import json

from database.Minio.connection import BRONZE_BUCKET
from database.Minio.crud import read_json_from_minio, save_silver_json, list_objects
from database.Mongo.crud import get_unprocessed_bronze_docs, save_silver_doc, insert_pipeline_log
from pipeline.etl.jobs.clean_logic import clean_and_validate_article
from pipeline.etl.registry import job

logger = logging.getLogger(__name__)


@job("fetch_unprocessed_bronze", outputs=["bronze_docs"])
def fetch_unprocessed_bronze(**kwargs):
    # This fetches tracking docs from Mongo
    unprocessed_docs = get_unprocessed_bronze_docs()
    logger.info(f"Found {len(unprocessed_docs)} unprocessed bronze documents in tracker.")
    return {"bronze_docs": unprocessed_docs}


@job("extract_html_content", inputs=["bronze_docs"], outputs=["extracted_docs"])
def extract_html_content(bronze_docs: list):
    extracted_docs = []
    
    for doc in bronze_docs:
        # doc is the MongoDB tracker doc. Let's assume it has a "minio_path" field.
        minio_path = doc.get("minio_path")
        if not minio_path:
            # Fallback if no minio path (legacy bronze)
            extracted_docs.append(doc)
            continue
            
        json_path = f"{minio_path}.json"
        metadata = read_json_from_minio(BRONZE_BUCKET, json_path)
        
        if metadata:
            # Merge tracker ID and minio metadata
            metadata["_str_id"] = str(doc.get("_id", ""))
            extracted_docs.append(metadata)
        else:
            logger.warning(f"Could not read metadata from MinIO for path: {json_path}")
            
    logger.info(f"Extracted content for {len(extracted_docs)} documents.")
    return {"extracted_docs": extracted_docs}


@job("validate_articles", inputs=["extracted_docs"], outputs=["valid_docs", "invalid_docs"])
def validate_articles(extracted_docs: list):
    valid_docs = []
    invalid_docs = []
    
    for doc in extracted_docs:
        bronze_id = doc.get("_str_id", "")
        url = doc.get("url")
        
        is_valid, error_msg, cleaned_data = clean_and_validate_article(doc)
        if is_valid:
            valid_docs.append({"doc": doc, "cleaned_data": cleaned_data})
        else:
            logger.warning(f"Validation failed for {bronze_id} ({url}): {error_msg}")
            invalid_docs.append({
                "stage": "silver_validate",
                "status": "rejected",
                "message": error_msg,
                "document_id": bronze_id,
                "url": url,
            })
            
    return {"valid_docs": valid_docs, "invalid_docs": invalid_docs}


@job("clean_article_text", inputs=["valid_docs"], outputs=["clean_docs"])
def clean_article_text(valid_docs: list):
    clean_docs = []
    
    for item in valid_docs:
        doc = item["doc"]
        cleaned_data = item["cleaned_data"]
        
        bronze_id = doc.get("_str_id", "")
        url = doc.get("url")
        
        # Additional cleaning logic can go here (e.g. whitespace strip)
        # We will prepare the Silver structure
        silver_doc = {
            "bronze_id": bronze_id,
            "url": url,
            "title": cleaned_data.get("title", ""),
            "original_text": cleaned_data.get("original_text", ""),
            "source_name": cleaned_data.get("source_name", ""),
            "image_url": cleaned_data.get("image_url", ""),
            "word_count": cleaned_data.get("word_count", 0),
            "cleaned_at": datetime.now(timezone.utc).isoformat(),
            "minio_path": f"articles/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}/{bronze_id}"
        }
        clean_docs.append(silver_doc)
        
    return {"clean_docs": clean_docs}


@job("save_to_silver", inputs=["clean_docs", "invalid_docs"])
def save_to_silver(clean_docs: list, invalid_docs: list):
    success_count = 0
    
    for silver_doc in clean_docs:
        try:
            minio_path = silver_doc.pop("minio_path")
            json_path = f"{minio_path}.json"
            
            # Save data to MinIO
            save_silver_json(json_path, silver_doc)
            
            # Update tracking in Mongo
            silver_doc["minio_path"] = minio_path # Restore for mongo
            save_silver_doc(silver_doc)
            
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to save silver doc to MinIO/Mongo: {e}")
            
    for log in invalid_docs:
        insert_pipeline_log(**log)
        
    logger.info(f"Saved {success_count} silver docs to MinIO.")
    return {"saved_silver": success_count, "failed_validation": len(invalid_docs)}
