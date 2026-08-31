"""
service/infrastructure/mongo/connection.py — MongoDB Client and Database Access.
Provides clean, singleton connection helpers for MongoDB.
"""

import logging
import os

from django.conf import settings
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)

_mongo_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    """
    Return singleton MongoClient initialized with standard URI and timeout.
    """
    global _mongo_client
    if _mongo_client is None:
        try:
            uri = settings.MONGO_URI if settings.configured else None
        except Exception:
            uri = None

        uri = uri or os.getenv(
            "MONGO_URI",
            "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin",
        )

        _mongo_client = MongoClient(
            uri,
            serverSelectionTimeoutMS=2000,
            connect=False,
        )
    return _mongo_client


def get_mongo_db() -> Database:
    """
    Return the primary MongoDB database instance.
    """
    try:
        db_name = settings.MONGO_DB_NAME if settings.configured else None
    except Exception:
        db_name = None

    db_name = db_name or os.getenv("MONGO_DB_NAME", "articlesDB")
    return get_mongo_client()[db_name]


def get_collection(name: str) -> Collection:
    """
    Return a native PyMongo Collection instance for the given collection name.
    """
    return get_mongo_db()[name]
