"""
pipeline/etl/gold.py — Gold stage: AI exam generation.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel

from database.Chroma.operations import add_article_vector
from database.Mongo.crud import (get_silver_by_id,
                                 get_unprocessed_silver_docs,
                                 insert_gold_doc,
                                 insert_pipeline_log,
                                 update_gold_doc)

logger = logging.getLogger(__name__)


def _recursive_dump(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _recursive_dump(value.model_dump())
    if isinstance(value, dict):
        return {k: _recursive_dump(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_recursive_dump(v) for v in value]
    return value


def run_ai_pipeline(original_text: str) -> Optional[dict]:
    """
    Run the LangGraph AI pipeline to generate an exam.
    """
    from pipeline.ai_core.graph import app

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
    logger.info("═══════════════════════════════════════════════")
    logger.info("  🟡 GOLD STAGE — AI Exam Generation")
    logger.info("═══════════════════════════════════════════════")

    unprocessed = get_unprocessed_silver_docs()
    if not unprocessed:
        logger.info("Nothing to process. Done.")
        return

    stats = {"completed": 0, "failed": 0}

    for doc in unprocessed:
        silver_id = doc["_str_id"]
        url = doc.get("url", "???")
        title = doc.get("title", "???")
        original_text = doc.get("original_text", "")

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
            gold_id = insert_gold_doc(gold_doc)
            if status_msg == "completed" and ai_result:
                summary = (
                    ai_result.get("analysis", {}).get("core", {}).get("summary", "")
                )
                if summary:
                    add_article_vector(
                        gold_id=gold_id, summary=summary, title=title, url=url
                    )
        except Exception as e:
            stats["failed"] += 1
            logger.error(f"  ⚠️  Gold insert failed [{silver_id}]: {e}")

        insert_pipeline_log(
            stage="gold",
            status=status_msg,
            message=f"Exam generation {status_msg}",
            document_id=silver_id,
            url=url,
        )

    insert_pipeline_log(
        stage="gold_batch",
        status="completed",
        message=f"Completed: {stats['completed']}, Failed: {stats['failed']}",
    )


def process_one_gold_async(silver_id: str, gold_id: str):
    silver_doc = get_silver_by_id(silver_id)
    if not silver_doc:
        update_gold_doc(
            gold_id=gold_id,
            update_data={
                "status": "failed",
                "error_message": "Silver document not found.",
            },
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
            "exams": [],
        }
        status_msg = "failed"

    try:
        update_gold_doc(gold_id=gold_id, update_data=update_data)
        if status_msg == "completed" and ai_result:
            summary = ai_result.get("analysis", {}).get("core", {}).get("summary", "")
            if summary:
                add_article_vector(
                    gold_id=gold_id,
                    summary=summary,
                    title=silver_doc.get("title", ""),
                    url=silver_doc.get("url", ""),
                )
    except Exception as e:
        logger.error(f"⚠️ Gold async update failed for gold_id: {gold_id}: {e}")

    insert_pipeline_log(
        stage="gold_one",
        status="completed" if status_msg == "completed" else "failed",
        message=f"Async exam generation {status_msg}",
        document_id=silver_id,
        url=silver_doc.get("url"),
    )


def main():
    process_gold()


if __name__ == "__main__":
    main()
