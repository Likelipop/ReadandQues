from bson import ObjectId

from .connection import article_collection, attempts_collection


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


def get_articles_by_user(user_id: int) -> list:
    try:
        cursor = article_collection.find({"user_id": user_id}).sort("created_at", -1)
        articles = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            articles.append(doc)
        return articles
    except Exception:
        return []


def get_completed_articles(limit=None, theme=None, genre=None) -> list:
    try:
        query = {"status": "completed"}
        if theme and theme != "All":
            query["theme"] = theme
        if genre and genre != "All":
            query["genre"] = genre

        cursor = article_collection.find(query).sort("created_at", -1)
        if limit:
            cursor = cursor.limit(limit)
        articles = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            articles.append(doc)
        return articles
    except Exception:
        return []


def save_exam_attempt(data: dict) -> str:
    try:
        result = attempts_collection.insert_one(data)
        return str(result.inserted_id)
    except Exception:
        return ""


def get_articles_by_ids(ids: list[str]) -> list[dict]:
    """Lấy nhiều articles theo list IDs, giữ nguyên thứ tự."""
    try:
        object_ids = [ObjectId(i) for i in ids]
        docs = list(
            article_collection.find(
                {"_id": {"$in": object_ids}},
                {
                    "title": 1,
                    "url": 1,
                    "theme": 1,
                    "genre": 1,
                    "image_url": 1,
                    "source_name": 1,
                },
            )
        )

        # Restore order by score
        id_to_doc = {str(d["_id"]): d for d in docs}
        ordered = []
        for i in ids:
            if i in id_to_doc:
                doc = id_to_doc[i]
                doc["id"] = str(doc["_id"])
                # Remove _id so it can be JSON serialized in the view response
                if "_id" in doc:
                    del doc["_id"]
                ordered.append(doc)
        return ordered
    except Exception:
        return []

def get_article_document_by_url(url: str):
    """Retrieve the most recent article document by URL from MongoDB."""
    try:
        # Sort by created_at descending to get the newest one if multiple exist
        doc = article_collection.find_one({"url": url}, sort=[("created_at", -1)])
        return doc
    except Exception as e:
        return None


def get_user_attempted_article_ids(user_id: int) -> set[str]:
    """Return a set of article_id strings for which user_id has at least one attempt."""
    if not user_id:
        return set()
    try:
        cursor = attempts_collection.find({"user_id": user_id}, {"article_id": 1})
        return {str(doc["article_id"]) for doc in cursor if "article_id" in doc}
    except Exception:
        return set()


# ── Medallion Pipeline CRUD Helpers ──────────────────────────────────────────

from datetime import datetime, timezone
from .connection import (bronze_collection, silver_collection, gold_collection, pipeline_logs_collection)


def find_existing_bronze_urls(urls: list[str]) -> set[str]:
    try:
        cursor = bronze_collection.find({"url": {"$in": urls}}, {"url": 1})
        return {doc["url"] for doc in cursor if "url" in doc}
    except Exception:
        return set()


def insert_bronze_doc(doc: dict) -> str:
    res = bronze_collection.insert_one(doc)
    return str(res.inserted_id)


def get_bronze_by_url(url: str) -> dict | None:
    try:
        return bronze_collection.find_one({"url": url})
    except Exception:
        return None


def get_bronze_by_id(pk: str) -> dict | None:
    try:
        return bronze_collection.find_one({"_id": ObjectId(pk)})
    except Exception:
        return None


def get_unprocessed_bronze_docs() -> list[dict]:
    try:
        processed_bronze_ids = set(
            silver_collection.distinct("bronze_id")
        )
        rejected_bronze_ids = set(
            pipeline_logs_collection.distinct("document_id", {"stage": "silver", "status": "rejected"})
        )
        exclude_ids = [ObjectId(bid) for bid in (processed_bronze_ids | rejected_bronze_ids) if ObjectId.is_valid(bid)]
        cursor = bronze_collection.find({"_id": {"$nin": exclude_ids}}).sort("crawled_at", 1)
        docs = []
        for d in cursor:
            d["_str_id"] = str(d["_id"])
            docs.append(d)
        return docs
    except Exception:
        return []


def save_silver_doc(doc: dict) -> str:
    res = silver_collection.insert_one(doc)
    return str(res.inserted_id)


def get_silver_by_bronze_id(bronze_id: str) -> dict | None:
    try:
        return silver_collection.find_one({"bronze_id": bronze_id})
    except Exception:
        return None


def get_silver_by_id(pk: str) -> dict | None:
    try:
        return silver_collection.find_one({"_id": ObjectId(pk)})
    except Exception:
        return None


def get_unprocessed_silver_docs() -> list[dict]:
    try:
        processed_silver_ids = set(
            gold_collection.distinct("silver_id")
        )
        exclude_ids = [ObjectId(sid) for sid in processed_silver_ids if ObjectId.is_valid(sid)]
        cursor = silver_collection.find({"_id": {"$nin": exclude_ids}}).sort("cleaned_at", 1)
        docs = []
        for d in cursor:
            d["_str_id"] = str(d["_id"])
            docs.append(d)
        return docs
    except Exception:
        return []


def insert_gold_doc(doc: dict) -> str:
    res = gold_collection.insert_one(doc)
    return str(res.inserted_id)


def update_gold_doc(gold_id: str, update_data: dict) -> bool:
    try:
        res = gold_collection.update_one({"_id": ObjectId(gold_id)}, {"$set": update_data})
        return res.modified_count > 0
    except Exception:
        return False


def insert_pipeline_log(
    stage: str,
    status: str,
    message: str = "",
    document_id: str | None = None,
    url: str | None = None,
) -> str:
    log_doc = {
        "stage": stage,
        "status": status,
        "message": message,
        "document_id": document_id,
        "url": url,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        res = pipeline_logs_collection.insert_one(log_doc)
        return str(res.inserted_id)
    except Exception:
        return ""


