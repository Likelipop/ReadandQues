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
