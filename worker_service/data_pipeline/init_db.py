"""
worker_service/data_pipeline/init_db.py — Initialize MongoDB database and collections.

Creates the 'articles' database with Bronze, Silver, Gold, Logs, and Attempts collections.
Sets up indexes for efficient querying across the pipeline.

Usage:
    python -m worker_service.data_pipeline.init_db
"""

from pymongo import ASCENDING, DESCENDING

from .utils.mongo_client import db, bronze_col, silver_col, gold_col, logs_col, attempts_col
from .pipeline_config import (
    BRONZE_COLLECTION,
    SILVER_COLLECTION,
    GOLD_COLLECTION,
    LOGS_COLLECTION,
    ATTEMPTS_COLLECTION,
)


def init_collections():
    """Create collections (if not exist) and set up indexes."""
    existing = db.list_collection_names()

    # ── Bronze Articles ─────────────────────────────────────────────────────
    if BRONZE_COLLECTION not in existing:
        db.create_collection(BRONZE_COLLECTION)
        print(f"  ✅ Created collection: {BRONZE_COLLECTION}")
    else:
        print(f"  ℹ️  Collection already exists: {BRONZE_COLLECTION}")

    bronze_col.create_index([("url", ASCENDING)], unique=True, name="idx_bronze_url_unique")
    bronze_col.create_index([("crawled_at", DESCENDING)], name="idx_bronze_crawled_at")
    print(f"  📇 Indexes set for {BRONZE_COLLECTION}")

    # ── Silver Articles ─────────────────────────────────────────────────────
    if SILVER_COLLECTION not in existing:
        db.create_collection(SILVER_COLLECTION)
        print(f"  ✅ Created collection: {SILVER_COLLECTION}")
    else:
        print(f"  ℹ️  Collection already exists: {SILVER_COLLECTION}")

    silver_col.create_index([("bronze_id", ASCENDING)], unique=True, name="idx_silver_bronze_id")
    silver_col.create_index([("cleaned_at", DESCENDING)], name="idx_silver_cleaned_at")
    silver_col.create_index([("url", ASCENDING)], name="idx_silver_url")
    print(f"  📇 Indexes set for {SILVER_COLLECTION}")

    # ── Gold Articles ───────────────────────────────────────────────────────
    if GOLD_COLLECTION not in existing:
        db.create_collection(GOLD_COLLECTION)
        print(f"  ✅ Created collection: {GOLD_COLLECTION}")
    else:
        print(f"  ℹ️  Collection already exists: {GOLD_COLLECTION}")

    gold_col.create_index([("silver_id", ASCENDING)], unique=True, sparse=True, name="idx_gold_silver_id")
    gold_col.create_index([("status", ASCENDING)], name="idx_gold_status")
    gold_col.create_index([("user_id", ASCENDING)], name="idx_gold_user_id")
    gold_col.create_index([("created_at", DESCENDING)], name="idx_gold_created_at")
    gold_col.create_index([("theme", ASCENDING)], name="idx_gold_theme")
    gold_col.create_index([("genre", ASCENDING)], name="idx_gold_genre")
    gold_col.create_index([("url", ASCENDING)], name="idx_gold_url")
    print(f"  📇 Indexes set for {GOLD_COLLECTION}")

    # ── Pipeline Logs ───────────────────────────────────────────────────────
    if LOGS_COLLECTION not in existing:
        db.create_collection(LOGS_COLLECTION)
        print(f"  ✅ Created collection: {LOGS_COLLECTION}")
    else:
        print(f"  ℹ️  Collection already exists: {LOGS_COLLECTION}")

    logs_col.create_index([("timestamp", DESCENDING)], name="idx_logs_timestamp")
    logs_col.create_index([("stage", ASCENDING), ("status", ASCENDING)], name="idx_logs_stage_status")
    print(f"  📇 Indexes set for {LOGS_COLLECTION}")

    # ── Attempts ────────────────────────────────────────────────────────────
    if ATTEMPTS_COLLECTION not in existing:
        db.create_collection(ATTEMPTS_COLLECTION)
        print(f"  ✅ Created collection: {ATTEMPTS_COLLECTION}")
    else:
        print(f"  ℹ️  Collection already exists: {ATTEMPTS_COLLECTION}")

    attempts_col.create_index([("user_id", ASCENDING), ("submitted_at", DESCENDING)], name="idx_attempts_user")
    attempts_col.create_index([("gold_article_id", ASCENDING)], name="idx_attempts_article")
    print(f"  📇 Indexes set for {ATTEMPTS_COLLECTION}")


def main():
    print(f"\n🔧 Initializing MongoDB database: '{db.name}'")
    print(f"   URI: {db.client.address}\n")
    init_collections()
    print(f"\n✅ Database '{db.name}' initialization complete.\n")


if __name__ == "__main__":
    main()
