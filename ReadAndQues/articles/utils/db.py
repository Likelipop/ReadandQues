from bson import ObjectId
from django.conf import settings
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Determine Mongo URI from settings / environment. Fall back to a local docker-compose mapping.
mongo_uri = getattr(settings, "MONGO_URI", None)
if not mongo_uri or mongo_uri.startswith("******"):
    # If you run Mongo locally via docker-compose with port mapping (27017 -> host), use localhost.
    # If Django runs inside Docker in same compose network, replace 'localhost' with 'mongo'.
    mongo_uri = "mongodb://admin:changeme@localhost:27017/mydb?authSource=admin"

client = MongoClient(
    mongo_uri,
    server_api=ServerApi("1"),
    serverSelectionTimeoutMS=5000,
)

# Try an initial ping to avoid surprising failures later; swallow exceptions so app can still start.
try:
    client.admin.command("ping")
except Exception:
    # Connection may not be available yet (e.g., docker-compose starting). Operations will raise later.
    pass

DB_NAME = getattr(settings, "MONGO_DB_NAME", "mydb")
db = client[DB_NAME]
article_collection = db["articles"]


def insert_article_document(data: dict) -> str:
    result = article_collection.insert_one(data)
    return str(result.inserted_id)


def update_article_document(pk: str, updates: dict) -> bool:
    try:
        result = article_collection.update_one({"_id": ObjectId(pk)}, {"$set": updates})
        return result.modified_count > 0
    except Exception:
        return False


def get_article_document_by_id(pk: str) -> dict | None:
    try:
        return article_collection.find_one({"_id": ObjectId(pk)})
    except Exception:
        return None
