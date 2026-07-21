"""
articles/services/exam_generation.py — AI Exam generation and database update logic.
"""

import uuid
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel

from AI_core.graph import app
from database.Mongo.crud import update_article_document, get_article_document_by_id
from database.Chroma.operations import add_article_vector

logger = logging.getLogger(__name__)


def _recursive_dump(value: Any) -> Any:
    """Recursively convert Pydantic models -> dicts."""
    if isinstance(value, BaseModel):
        return _recursive_dump(value.model_dump())
    if isinstance(value, dict):
        return {k: _recursive_dump(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_recursive_dump(v) for v in value]
    return value


def run_ai_exam_pipeline(original_text: str) -> Optional[Dict[str, Any]]:
    """
    Invokes the AI_core LangGraph pipeline to generate an exam.
    """
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
        logger.error(f"[AI Exam Pipeline] LangGraph error: {exc}")
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


def generate_exam_for_article_async(article_id: str, original_text: str, title: str, url: str):
    """
    Background worker thread function to run AI exam generation and update MongoDB & ChromaDB.
    """
    logger.info(f"🔄 Starting background AI exam generation for article_id: {article_id}")
    ai_result = run_ai_exam_pipeline(original_text)

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
        updated = update_article_document(article_id, update_data)
        logger.info(f"{'✅' if status_msg == 'completed' else '❌'} Exam generation status: {status_msg} for article {article_id}")

        if status_msg == "completed" and ai_result:
            summary = ai_result.get("analysis", {}).get("core", {}).get("summary", "")
            if summary:
                add_article_vector(
                    gold_id=article_id,
                    summary=summary,
                    title=title,
                    url=url
                )
            # Rebuild BM25 index with new article
            try:
                from database.BM25.connection import rebuild_index
                rebuild_index()
            except Exception as e:
                logger.error(f"Failed to rebuild BM25 index after adding article {article_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to update article document {article_id}: {e}")
