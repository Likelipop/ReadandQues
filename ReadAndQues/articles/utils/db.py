from bson import ObjectId
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from django.conf import settings


def get_mongo_db():
    # Ví dụ bạn cấu hình MONGO_URI = "mongodb://localhost:27017/" trong settings.py
    client = MongoClient(
        getattr(settings, "MONGO_URI", "mongodb://localhost:27017/"),
        server_api=ServerApi("1"),
    )
    # Tên database của bạn, ví dụ: english_quiz_db
    return client[getattr(settings, "MONGO_DB_NAME", "default")]


def get_article_collection():
    return get_mongo_db()["articles"]


def insert_article_document(document: dict) -> str:
    """Insert a new article document and return its stringified ObjectId."""
    result = get_article_collection().insert_one(document)
    return str(result.inserted_id)


def get_article_document_by_id(pk: str) -> dict | None:
    """Return a stored article document by its MongoDB ObjectId string."""
    try:
        object_id = ObjectId(pk)
    except Exception:
        return None

    return get_article_collection().find_one({"_id": object_id})


def update_article_document(pk: str, updates: dict) -> bool:
    """Update an article document by its MongoDB ObjectId string."""
    try:
        object_id = ObjectId(pk)
    except Exception:
        return False

    result = get_article_collection().update_one({"_id": object_id}, {"$set": updates})
    return result.modified_count > 0
