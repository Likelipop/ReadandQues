from bson import ObjectId
from django.conf import settings
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Create client once
client = MongoClient(
    getattr(settings, "MONGO_URI", "mongodb://localhost:27017/"),
    server_api=ServerApi("1"),
)

db = client[getattr(settings, "MONGO_DB_NAME", "read_and_ques_db")]
article_collection = db["articles"]


def insert_article_document(data: dict) -> str:
    result = article_collection.insert_one(data)
    return str(result.inserted_id)


def get_article_document_by_id(pk: str) -> dict | None:
    try:
        return article_collection.find_one({"_id": ObjectId(pk)})
    except Exception:
        return None