"""
worker_service/data_pipeline/gold.py — Gold stage: AI exam generation.

Reads clean documents from silver_articles that have not yet been processed
into gold_articles, runs the LangGraph AI pipeline to generate IELTS exams,
and writes the final enriched documents into gold_articles.

Usage:
    python -m worker_service.data_pipeline.gold
"""

import sys
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from .utils.mongo_client import silver_col, gold_col, logs_col
from worker_service.ai_core.chroma_client import articles_collection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ensure worker_service is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _recursive_dump(value: Any) -> Any:
    """Recursively convert Pydantic models → plain dicts for MongoDB storage."""
    if isinstance(value, BaseModel):
        return _recursive_dump(value.model_dump())
    if isinstance(value, dict):
        return {k: _recursive_dump(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_recursive_dump(v) for v in value]
    return value


def get_unprocessed_silver_docs() -> list[dict]:
    """Find silver documents that have not yet been processed into gold."""
    existing_silver_ids = set()
    for doc in gold_col.find({}, {"silver_id": 1}):
        sid = doc.get("silver_id")
        if sid:
            existing_silver_ids.add(sid)

    new_docs = []
    for doc in silver_col.find().sort("cleaned_at", -1):
        doc_id = str(doc["_id"])
        if doc_id not in existing_silver_ids:
            doc["_str_id"] = doc_id
            new_docs.append(doc)

    return new_docs


def run_ai_pipeline(original_text: str) -> Optional[dict]:
    """
    Run the LangGraph AI pipeline to generate an exam.

    Returns dict with keys: theme, genre, analysis, exams, status
    Or None if pipeline fails.
    """
    from worker_service.ai_core.graph import app

    session_id = f"session_{uuid.uuid4().hex}"
    graph_config = {"configurable": {"thread_id": session_id}}

    initial_state = {
        "original_text": original_text,
        "exam_config": {},
        "semantic_analysis": {},
        "raw_quizzes": [],
        "verified_quizzes": [],
        "retry_count": 0,
        "token_log": [],
        "final_exam": {},
    }

    try:
        result = app.invoke(initial_state, graph_config)
    except Exception as exc:
        logger.error(f"[gold] LangGraph pipeline error: {exc}")
        return None

    result = _recursive_dump(result)

    final_exam = result.get("final_exam")
    if not final_exam:
        return None

    semantic_analysis = result.get("semantic_analysis") or {}
    theme = semantic_analysis.get("theme", "General")
    genre = semantic_analysis.get("genre", "general")

    return {
        "theme": theme,
        "genre": genre,
        "analysis": semantic_analysis,
        "exams": [final_exam],
        "original_text": result.get("original_text", original_text),
        "status": "completed",
    }


def process_gold():
    """Main gold processing loop."""
    logger.info("═══════════════════════════════════════════════")
    logger.info("  🟡 GOLD STAGE — AI Exam Generation")
    logger.info("═══════════════════════════════════════════════")

    unprocessed = get_unprocessed_silver_docs()
    logger.info(f"📦 Found {len(unprocessed)} unprocessed silver documents\n")

    if not unprocessed:
        logger.info("Nothing to process. Done.")
        return

    stats = {"completed": 0, "failed": 0}

    for doc in unprocessed:
        silver_id = doc["_str_id"]
        url = doc.get("url", "???")
        title = doc.get("title", "???")
        original_text = doc.get("original_text", "")

        logger.info(f"  🔄 Processing [{silver_id}] {title[:60]}...")

        ai_result = run_ai_pipeline(original_text)

        gold_doc = {
            "silver_id": silver_id,
            "url": url,
            "title": title,
            "original_text": original_text,
            "source_name": doc.get("source_name", "Unknown"),
            "image_url": doc.get("image_url"),
            "image_urls": doc.get("image_urls", []),
            "user_id": doc.get("user_id"),
            "created_at": datetime.now(timezone.utc),
        }

        if ai_result:
            gold_doc.update(ai_result)
            stats["completed"] += 1
            status_msg = "completed"
        else:
            gold_doc["status"] = "failed"
            gold_doc["error_message"] = "AI pipeline failed to generate exam"
            gold_doc["exams"] = []
            stats["failed"] += 1
            status_msg = "failed"

        try:
            result = gold_col.insert_one(gold_doc)
            logger.info(f"  {'✅' if status_msg == 'completed' else '❌'} "
                        f"Gold [{status_msg}]: {result.inserted_id}")
            
            # If successful and we have AI analysis, embed it in ChromaDB
            if status_msg == "completed" and articles_collection and ai_result:
                summary = ai_result.get("analysis", {}).get("core", {}).get("summary", "")
                if summary:
                    articles_collection.add(
                        documents=[summary],
                        metadatas=[{"title": title, "url": url}],
                        ids=[str(result.inserted_id)]
                    )
        except Exception as e:
            stats["failed"] += 1
            logger.error(f"  ⚠️  Gold insert failed [{silver_id}]: {e}")

        logs_col.insert_one({
            "stage": "gold",
            "document_id": silver_id,
            "url": url,
            "status": status_msg,
            "message": f"Exam generation {status_msg}",
            "timestamp": datetime.now(timezone.utc),
        })

    logger.info(f"\n📈 Gold complete: {stats['completed']} completed, {stats['failed']} failed")

    logs_col.insert_one({
        "stage": "gold_batch",
        "document_id": None,
        "status": "completed",
        "message": f"Completed: {stats['completed']}, Failed: {stats['failed']}",
        "timestamp": datetime.now(timezone.utc),
    })


def process_one_gold_async(silver_id: str, gold_id: str):
    """
    Run AI pipeline for a single article in a background thread.
    Updates the existing gold_articles document (which starts as pending).
    """
    from bson import ObjectId

    logger.info(f"🔄 Starting Gold async thread for silver_id: {silver_id}, gold_id: {gold_id}")
    
    # Get original_text from silver
    silver_doc = silver_col.find_one({"_id": ObjectId(silver_id)})
    if not silver_doc:
        logger.error(f"❌ Gold async failed: Silver doc {silver_id} not found.")
        gold_col.update_one(
            {"_id": ObjectId(gold_id)},
            {"$set": {"status": "failed", "error_message": "Silver document not found."}}
        )
        return

    original_text = silver_doc.get("original_text", "")
    ai_result = run_ai_pipeline(original_text)

    if ai_result:
        update_data = ai_result
        status_msg = "completed"
    else:
        update_data = {
            "status": "failed",
            "error_message": "AI pipeline failed to generate exam",
            "exams": []
        }
        status_msg = "failed"

    try:
        gold_col.update_one(
            {"_id": ObjectId(gold_id)},
            {"$set": update_data}
        )
        logger.info(f"{'✅' if status_msg == 'completed' else '❌'} Gold async [{status_msg}] for gold_id: {gold_id}")
        
        # If successful and we have AI analysis, embed it in ChromaDB
        if status_msg == "completed" and articles_collection and ai_result:
            summary = ai_result.get("analysis", {}).get("core", {}).get("summary", "")
            if summary:
                articles_collection.add(
                    documents=[summary],
                    metadatas=[{"title": silver_doc.get("title", ""), "url": silver_doc.get("url", "")}],
                    ids=[gold_id]
                )
    except Exception as e:
        logger.error(f"⚠️ Gold async update failed for gold_id: {gold_id}: {e}")

    logs_col.insert_one({
        "stage": "gold_one",
        "document_id": silver_id,
        "url": silver_doc.get("url"),
        "status": status_msg,
        "message": f"Async exam generation {status_msg}",
        "timestamp": datetime.now(timezone.utc),
    })


def main():
    process_gold()


if __name__ == "__main__":
    main()
