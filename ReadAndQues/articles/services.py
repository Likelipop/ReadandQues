"""
articles/services.py — Service layer: orchestrates the LangGraph pipeline and
maps its output to the MongoDB document payload.

process_and_analyze_article(url) → Optional[dict]
  Returns a dict ready to be $set into the article document via update_article_document().
"""

import uuid
from typing import Any, Optional

from pydantic import BaseModel

from ai_core.graph import app


def _recursive_dump(value: Any) -> Any:
    """Recursively convert Pydantic models → plain dicts so MongoDB can store them."""
    if isinstance(value, BaseModel):
        return _recursive_dump(value.model_dump())
    if isinstance(value, dict):
        return {k: _recursive_dump(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_recursive_dump(v) for v in value]
    return value


def process_and_analyze_article(url: str, original_text: str) -> Optional[dict]:
    """
    Run the 4-node LangGraph pipeline on an already-crawled article.

    Parameters
    ----------
    url           : canonical URL of the article (for storage)
    original_text : plain-text body of the article

    Returns
    -------
    A dict containing all fields to be written to the MongoDB article document,
    or None if the pipeline fails entirely.
    """
    # Each invocation gets a unique LangGraph thread id — safe across multi-worker servers
    session_id   = f"session_{uuid.uuid4().hex}"
    graph_config = {"configurable": {"thread_id": session_id}}

    initial_state = {
        "original_text":     original_text,
        # Remaining state fields are initialised inside node_analyzer
        "exam_config":       {},
        "semantic_analysis": {},
        "raw_quizzes":       [],
        "verified_quizzes":  [],
        "retry_count":       0,
        "token_log":         [],
        "final_exam":        {},
    }

    try:
        result = app.invoke(initial_state, graph_config)
    except Exception as exc:
        print(f"[services] LangGraph pipeline error: {exc}")
        return None

    result = _recursive_dump(result)

    final_exam = result.get("final_exam")
    if not final_exam:
        return None

    # semantic_analysis goes to articles.analysis field in MongoDB
    semantic_analysis = result.get("semantic_analysis") or {}
    theme = semantic_analysis.get("theme", "General")
    genre = semantic_analysis.get("genre", "general")

    return {
        "theme":    theme,
        "genre":    genre,
        "analysis": semantic_analysis,           # SemanticAnalysis dict — new field
        "exams":    [final_exam],                # List[Exam] — embedded 1-to-N
        "status":   "completed",
    }