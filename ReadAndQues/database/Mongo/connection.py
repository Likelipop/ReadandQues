import os
import socket
import logging
from django.conf import settings
from pymongo import MongoClient
from pymongo.server_api import ServerApi

logger = logging.getLogger(__name__)

_mongo_client: MongoClient | None = None


def get_setting(name: str, default: str) -> str:
    try:
        if settings.configured:
            val = getattr(settings, name, None)
            if val is not None:
                return val
    except Exception:
        pass
    return os.getenv(name, default)


def get_mongo_uri() -> str:
    mongo_uri = get_setting("MONGO_URI", "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin")
    if not mongo_uri or mongo_uri.startswith("******"):
        mongo_uri = os.getenv(
            "MONGO_URI",
            "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin",
        )

    if "@mongo:" in mongo_uri:
        try:
            socket.gethostbyname("mongo")
        except socket.gaierror:
            mongo_uri = mongo_uri.replace("@mongo:", "@localhost:")
    return mongo_uri


def get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        uri = get_mongo_uri()
        _mongo_client = MongoClient(
            uri,
            server_api=ServerApi("1"),
            serverSelectionTimeoutMS=5000,
            connect=False,
        )
    return _mongo_client


def get_mongo_db():
    client = get_mongo_client()
    db_name = get_setting("MONGO_DB_NAME", "articlesDB")
    return client[db_name]


class LazyMongoCollection:
    """Proxy object that delays MongoDB collection lookup until first attribute access."""

    def __init__(self, collection_name: str):
        self._collection_name = collection_name
        self._coll = None

    def _get_coll(self):
        if self._coll is None:
            db = get_mongo_db()
            self._coll = db[self._collection_name]
        return self._coll

    def __getattr__(self, name: str):
        return getattr(self._get_coll(), name)

    def __getitem__(self, key):
        return self._get_coll()[key]


# Lazy collection proxies (zero network I/O at import time)
article_collection = LazyMongoCollection("gold_articles")
gold_collection = LazyMongoCollection("gold_articles")
gold_homepage_collection = LazyMongoCollection("gold_homepage_articles")
gold_ai_collection = LazyMongoCollection("gold_ai_articles")
silver_collection = LazyMongoCollection("silver_articles")
bronze_collection = LazyMongoCollection("bronze_articles")
pipeline_logs_collection = LazyMongoCollection("pipeline_logs")
attempts_collection = LazyMongoCollection("attempts")
smart_paraphrase_collection = LazyMongoCollection("smart_paraphrase_cache")
rss_links_collection = LazyMongoCollection("rss_links")
reading_history_collection = LazyMongoCollection("reading_history")
user_highlights_collection = LazyMongoCollection("user_highlights")
homepage_sections_collection = LazyMongoCollection("homepage_sections")
vocab_tracking_collection = LazyMongoCollection("vocab_tracking")
migrations_collection = LazyMongoCollection("_migrations")

# New clean-arch collections
article_index_collection = LazyMongoCollection("article_index")
exams_collection = LazyMongoCollection("exams")
