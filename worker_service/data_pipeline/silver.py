"""
worker_service/data_pipeline/silver.py — Silver stage: data cleaning & validation.

Reads unprocessed documents from bronze_articles (those not yet in silver_articles),
validates and cleans them, and writes clean documents into silver_articles.
Dirty/rejected documents are logged to pipeline_logs.

Usage:
    python -m worker_service.data_pipeline.silver
"""

import logging
from datetime import datetime, timezone

from bson import ObjectId

from .pipeline_config import SILVER_MIN_WORD_COUNT, SILVER_MAX_WORD_COUNT
from .utils.formatter import to_markdown
from .utils.mongo_client import bronze_col, silver_col, logs_col

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_unprocessed_bronze_docs() -> list[dict]:
    """Find bronze documents that have not yet been cleaned into silver."""
    # Get all bronze_ids already in silver
    existing_bronze_ids = set()
    for doc in silver_col.find({}, {"bronze_id": 1}):
        bid = doc.get("bronze_id")
        if bid:
            existing_bronze_ids.add(bid)

    # Find bronze docs not yet processed
    new_docs = []
    for doc in bronze_col.find().sort("crawled_at", -1):
        doc_id = str(doc["_id"])
        if doc_id not in existing_bronze_ids:
            doc["_str_id"] = doc_id
            new_docs.append(doc)

    return new_docs


def validate_document(doc: dict) -> tuple[bool, list[str]]:
    """
    Validate a bronze document. Returns (is_valid, list_of_issues).
    """
    issues = []

    # Title check
    title = (doc.get("title") or "").strip()
    if not title:
        issues.append("Missing or empty title")

    # Text check
    raw_text = (doc.get("raw_text") or "").strip()
    if not raw_text:
        issues.append("Missing or empty raw_text")
    else:
        word_count = len(raw_text.split())
        if word_count < SILVER_MIN_WORD_COUNT:
            issues.append(f"Text too short: {word_count} words (min: {SILVER_MIN_WORD_COUNT})")
        if word_count > SILVER_MAX_WORD_COUNT:
            issues.append(f"Text suspiciously long: {word_count} words (max: {SILVER_MAX_WORD_COUNT})")

    # URL check
    url = (doc.get("url") or "").strip()
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        issues.append(f"Invalid URL: '{url}'")

    # Image URL validation
    image_url = doc.get("image_url")
    if image_url and not (image_url.startswith("http://") or image_url.startswith("https://")):
        issues.append(f"Invalid image_url: '{image_url}'")

    is_valid = len(issues) == 0
    return is_valid, issues


def clean_document(doc: dict) -> dict:
    """Transform a validated bronze document into a clean silver document."""
    raw_text = (doc.get("raw_text") or "").strip()
    original_text = to_markdown(raw_text)
    word_count = len(raw_text.split())

    # Clean image_urls — filter out invalid ones
    image_urls = []
    for img in (doc.get("image_urls") or []):
        if img and (img.startswith("http://") or img.startswith("https://")):
            image_urls.append(img.strip())

    image_url = doc.get("image_url")
    if image_url and not (image_url.startswith("http://") or image_url.startswith("https://")):
        image_url = image_urls[0] if image_urls else None

    return {
        "bronze_id": doc["_str_id"],
        "url": doc["url"].strip(),
        "title": doc["title"].strip(),
        "original_text": original_text,
        "source_name": (doc.get("source_name") or "Unknown").strip(),
        "image_url": image_url,
        "image_urls": image_urls,
        "word_count": word_count,
        "user_id": doc.get("user_id"),
        "quality_flags": [],  # can be extended with NLP quality checks
        "cleaned_at": datetime.now(timezone.utc),
    }


def process_silver():
    """Main silver processing loop."""
    logger.info("═══════════════════════════════════════════════")
    logger.info("  ⚪ SILVER STAGE — Data Cleaning & Validation")
    logger.info("═══════════════════════════════════════════════")

    unprocessed = get_unprocessed_bronze_docs()
    logger.info(f"📦 Found {len(unprocessed)} unprocessed bronze documents\n")

    if not unprocessed:
        logger.info("Nothing to process. Done.")
        return

    stats = {"cleaned": 0, "rejected": 0}

    for doc in unprocessed:
        url = doc.get("url", "???")
        bronze_id = doc["_str_id"]

        is_valid, issues = validate_document(doc)

        if not is_valid:
            stats["rejected"] += 1
            logger.warning(f"  ❌ Rejected [{bronze_id}] {url}")
            for issue in issues:
                logger.warning(f"     → {issue}")

            logs_col.insert_one({
                "stage": "silver",
                "document_id": bronze_id,
                "url": url,
                "status": "rejected",
                "message": "; ".join(issues),
                "timestamp": datetime.now(timezone.utc),
            })
            continue

        silver_doc = clean_document(doc)

        try:
            result = silver_col.insert_one(silver_doc)
            stats["cleaned"] += 1
            logger.info(f"  ✅ Cleaned [{bronze_id}] → silver {result.inserted_id}")
        except Exception as e:
            stats["rejected"] += 1
            logger.warning(f"  ⚠️  Insert failed [{bronze_id}]: {e}")
            logs_col.insert_one({
                "stage": "silver",
                "document_id": bronze_id,
                "url": url,
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc),
            })

    logger.info(f"\n📈 Silver complete: {stats['cleaned']} cleaned, {stats['rejected']} rejected")

    logs_col.insert_one({
        "stage": "silver_batch",
        "document_id": None,
        "status": "completed",
        "message": f"Cleaned: {stats['cleaned']}, Rejected: {stats['rejected']}",
        "timestamp": datetime.now(timezone.utc),
    })


def process_one_silver(bronze_id: str) -> dict:
    """
    Process a single bronze document synchronously (used for user imports).
    Returns dict with keys: success, silver_id, silver_doc, error.
    """
    try:
        doc = bronze_col.find_one({"_id": ObjectId(bronze_id)})
    except Exception as e:
        return {"success": False, "error": f"Invalid bronze_id format: {e}"}

    if not doc:
        return {"success": False, "error": "Bronze document not found."}

    doc["_str_id"] = str(doc["_id"])

    # Check if already processed
    existing_silver = silver_col.find_one({"bronze_id": doc["_str_id"]})
    if existing_silver:
        return {
            "success": True, 
            "silver_id": str(existing_silver["_id"]),
            "silver_doc": existing_silver,
            "already_exists": True
        }

    is_valid, issues = validate_document(doc)
    if not is_valid:
        msg = "; ".join(issues)
        logs_col.insert_one({
            "stage": "silver_one",
            "document_id": doc["_str_id"],
            "url": doc.get("url"),
            "status": "rejected",
            "message": msg,
            "timestamp": datetime.now(timezone.utc),
        })
        return {"success": False, "error": f"Article validation failed: {msg}"}

    silver_doc = clean_document(doc)
    try:
        result = silver_col.insert_one(silver_doc)
        silver_doc["_id"] = result.inserted_id
        return {
            "success": True,
            "silver_id": str(result.inserted_id),
            "silver_doc": silver_doc,
            "already_exists": False
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    process_silver()


if __name__ == "__main__":
    main()
