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
