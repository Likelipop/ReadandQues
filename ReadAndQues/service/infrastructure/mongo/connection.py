"""
service/infrastructure/mongo/connection.py — Minimalist MongoDB Connection.
"""

import logging
import os

from django.conf import settings
from pymongo import MongoClient
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

_mongo_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    """Return singleton MongoClient with connect=False lazy initialization."""
    global _mongo_client
    if _mongo_client is None:
        try:
            uri = settings.MONGO_URI if settings.configured else os.getenv(
                "MONGO_URI",
                "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin",
            )
        except Exception:
            uri = os.getenv(
                "MONGO_URI",
                "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin",
            )
        _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=5000, connect=False)
    return _mongo_client


def get_mongo_db():
    """Return default MongoDB database instance."""
    try:
        db_name = settings.MONGO_DB_NAME if settings.configured else os.getenv("MONGO_DB_NAME", "articlesDB")
    except Exception:
        db_name = os.getenv("MONGO_DB_NAME", "articlesDB")
    return get_mongo_client()[db_name]


def get_collection(name: str) -> Collection:
    """Return native PyMongo Collection instance."""
    return get_mongo_db()[name]
