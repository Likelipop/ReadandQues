"""
worker_service/data_pipeline/utils/mongo_client.py — Standalone MongoDB client.

No Django dependency. Used by all pipeline stages.
"""

from pymongo import MongoClient
from pymongo.server_api import ServerApi

from ..pipeline_config import (
    MONGO_URI,
    DB_NAME,
    BRONZE_COLLECTION,
    SILVER_COLLECTION,
    GOLD_COLLECTION,
    LOGS_COLLECTION,
    ATTEMPTS_COLLECTION,
)

client = MongoClient(
    MONGO_URI,
    server_api=ServerApi("1"),
    serverSelectionTimeoutMS=5000,
)

# Ping on import — swallow exceptions so scripts can still start
try:
    client.admin.command("ping")
except Exception:
    pass

db = client[DB_NAME]

bronze_col = db[BRONZE_COLLECTION]
silver_col = db[SILVER_COLLECTION]
gold_col = db[GOLD_COLLECTION]
logs_col = db[LOGS_COLLECTION]
attempts_col = db[ATTEMPTS_COLLECTION]
