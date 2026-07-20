"""
articles/services.py — Service layer: orchestrates business logic and AI pipelines.
"""

import threading
import logging
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, timezone

from django.db import transaction
from pydantic import BaseModel

from accounts.models import UserProfile
from worker_service.data_pipeline.bronze_one import ingest_one as bronze_ingest
from worker_service.data_pipeline.silver import process_one_silver
from worker_service.data_pipeline.gold import process_one_gold_async
from worker_service.ai_core.chroma_client import articles_collection

from .utils.db import insert_article_document, article_collection

logger = logging.getLogger(__name__)


def deduct_user_star(user) -> Tuple[bool, str]:
    """
    Atomically deducts one star from the user's profile.
    Returns (success, error_message).
    """
    try:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=user)
            if profile.stars <= 0:
                return False, "NO_STARS"
            
            profile.stars -= 1
            profile.save()
            return True, ""
    except Exception as e:
        logger.error(f"Error deducting star for user {user.id}: {e}")
        return False, "Lỗi hệ thống khi cập nhật số lượng Star."


def refund_user_star(user):
    """
    Atomically refunds one star to the user's profile.
    """
    try:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=user)
            profile.stars += 1
            profile.save()
    except Exception as e:
        logger.error(f"Error refunding star for user {user.id}: {e}")


def import_and_trigger_pipeline(url: str, user_id: int) -> Tuple[bool, str, Optional[str]]:
    """
    Runs the bronze and silver ingestion pipelines synchronously.
    If successful, inserts a pending document and kicks off the gold pipeline asynchronously.
    Returns (success, error_message, inserted_id).
    """
    if not url:
        return False, "Vui lòng nhập một URL bài báo hợp lệ!", None

    # 1. Bronze stage: Crawl content
    bronze_result = bronze_ingest(url, user_id=user_id)
    if not bronze_result.get("success"):
        return False, bronze_result.get("error", "Không thể trích xuất nội dung từ bài báo này."), None

    # 2. Silver stage: Clean and validate
    silver_result = process_one_silver(bronze_result["bronze_id"])
    if not silver_result.get("success"):
        return False, silver_result.get("error", "Bài báo không đủ điều kiện (quá ngắn hoặc quá dài)."), None

    silver_doc = silver_result.get("silver_doc", {})

    # 3. Create pending document
    pending_document = {
        "silver_id": silver_result["silver_id"],
        "url": url,
        "title": silver_doc.get("title", ""),
        "original_text": silver_doc.get("original_text", ""),
        "source_name": silver_doc.get("source_name", "Unknown"),
        "image_url": silver_doc.get("image_url"),
        "image_urls": silver_doc.get("image_urls") or [],
        "status": "pending",
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    inserted_id = insert_article_document(pending_document)

    # 4. Gold stage: Async AI Pipeline
    thread = threading.Thread(
        target=process_one_gold_async,
        args=(silver_result["silver_id"], inserted_id),
        daemon=True,
    )
    thread.start()

    return True, "", inserted_id


def get_related_articles_via_chroma(article, exclude_id: str, limit: int = 5) -> List[Dict]:
    """
    Queries ChromaDB for semantically similar articles based on the summary.
    Returns a list of related MongoDB article documents.
    """
    if not articles_collection or not hasattr(article, 'analysis') or not article.analysis:
        return []

    # Safely extract summary
    summary = ""
    if hasattr(article.analysis, "core"):
        summary = article.analysis.core.summary
    elif isinstance(article.analysis, dict):
        summary = article.analysis.get("core", {}).get("summary", "")

    if not summary:
        return []

    try:
        # Query ChromaDB
        results = articles_collection.query(
            query_texts=[summary],
            n_results=limit + 1
        )
        
        if not results or not results['ids']:
            return []
            
        related_ids = [str(r_id) for r_id in results['ids'][0] if str(r_id) != str(exclude_id)][:limit]
        
        if not related_ids:
            return []

        from bson import ObjectId
        object_ids = [ObjectId(rid) for rid in related_ids]
        
        # Fetch from MongoDB
        cursor = article_collection.find({"_id": {"$in": object_ids}})
        related_docs = {str(d["_id"]): d for d in cursor}
        
        # Maintain order returned by vector search
        related_articles = []
        for rid in related_ids:
            if rid in related_docs:
                r_doc = related_docs[rid]
                r_doc["id"] = str(r_doc["_id"])
                related_articles.append(r_doc)
                
        return related_articles
    except Exception as e:
        logger.error(f"Error fetching related articles from ChromaDB: {e}")
        return []