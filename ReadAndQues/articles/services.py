import uuid
from typing import Any, Optional

from pydantic import BaseModel

from ai_core.graph import app
from .utils.crawler import crawl_article_content


def _recursive_dump(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _recursive_dump(value.model_dump())
    if isinstance(value, dict):
        return {k: _recursive_dump(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_recursive_dump(v) for v in value]
    return value


def process_and_analyze_article(url: str) -> Optional[dict]:
    crawl_result = crawl_article_content(url)
    if not crawl_result.get("success"):
        return None

    title = crawl_result.get("title", "").strip()
    plain_text = crawl_result.get("content", "").strip()

    session_id = f"session_{uuid.uuid4().hex}"
    graph_config = {"configurable": {"thread_id": session_id}}

    ai_result = app.invoke({"original_text": plain_text}, graph_config)
    ai_result = _recursive_dump(ai_result)

    return {
        "url": url,
        "title": title,
        "original_text": plain_text,
        "source_name": "Unknown",
        "exams": [ai_result.get("final_exam")],
        "status": "completed",
    }