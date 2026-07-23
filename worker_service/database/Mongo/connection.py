"""
worker_service/database/Mongo/connection.py — Standalone MongoDB connection.

No Django dependency. Used across worker_service pipeline and services.
"""

import os

from pymongo import MongoClient
from pymongo.server_api import ServerApi

from worker_service.data_pipeline.pipeline_config import (ATTEMPTS_COLLECTION,
                                                          BRONZE_COLLECTION,
                                                          DB_NAME,
                                                          GOLD_COLLECTION,
                                                          LOGS_COLLECTION,
                                                          MONGO_URI,
                                                          SILVER_COLLECTION)

client = MongoClient(
    MONGO_URI,
    server_api=ServerApi("1"),
    serverSelectionTimeoutMS=5000,
    connect=False,
)

db = client[DB_NAME]

bronze_col = db[BRONZE_COLLECTION]
silver_col = db[SILVER_COLLECTION]
gold_col = db[GOLD_COLLECTION]
logs_col = db[LOGS_COLLECTION]
attempts_col = db[ATTEMPTS_COLLECTION]
