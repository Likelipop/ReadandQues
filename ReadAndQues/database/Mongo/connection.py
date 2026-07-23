from django.conf import settings
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Determine Mongo URI from settings / environment. Fall back to a local docker-compose mapping.
mongo_uri = getattr(settings, "MONGO_URI", None)
if not mongo_uri or mongo_uri.startswith("******"):
    mongo_uri = os.getenv(
        "MONGO_URI",
        "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin",
    )


def get_mongo_client() -> MongoClient:
    client = MongoClient(
        mongo_uri,
        server_api=ServerApi("1"),
        serverSelectionTimeoutMS=5000,
        connect=False,
    )
    return client


client = get_mongo_client()
DB_NAME = getattr(settings, "MONGO_DB_NAME", "articles")
db = client[DB_NAME]
article_collection = db["gold_articles"]
attempts_collection = db["attempts"]
