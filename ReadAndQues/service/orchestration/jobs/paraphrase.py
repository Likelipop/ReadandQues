"""
service/orchestration/jobs/paraphrase.py — Smart Paraphrase pipeline jobs.

Jobs:
  find_cached_paraphrase  — lookup MongoDB cache by (article_id, paragraph_hash, range)
  run_paraphrase_llm      — call LangGraph SmartParaphrase if no cache hit
  save_paraphrase         — persist new paraphrase result to MongoDB cache
"""

import logging

from service.repositories.content_repository import ContentRepository
from service.orchestration.configuration import job

logger = logging.getLogger(__name__)


@job(
    "find_cached_paraphrase",
    inputs=["article_id", "paragraph_hash", "start_idx", "end_idx"],
    outputs=["cached_paraphrase"],
)
def find_cached_paraphrase(
    article_id: str, paragraph_hash: str, start_idx: int, end_idx: int
):
    """Check MongoDB smart_paraphrase_cache for an exact match."""
    content_repo = ContentRepository()
    doc = content_repo.find_paraphrase(article_id, paragraph_hash, start_idx, end_idx)
    return {"cached_paraphrase": doc}


@job(
    "run_paraphrase_llm",
    inputs=[
        "cached_paraphrase",
        "highlighted_text",
        "paragraph_text",
        "article_id",
        "paragraph_hash",
        "start_idx",
        "end_idx",
    ],
    outputs=["paraphrase_data"],
)
def run_paraphrase_llm(
    cached_paraphrase: dict,
    highlighted_text: str,
    paragraph_text: str,
    article_id: str,
    paragraph_hash: str,
    start_idx: int,
    end_idx: int,
):
    """Return cached result if available; otherwise run LangGraph SmartParaphrase."""
    if cached_paraphrase:
        logger.info(f"[paraphrase] Cache hit for article {article_id}")
        return {"paraphrase_data": cached_paraphrase}

    logger.info(f"[paraphrase] Cache miss. Running SmartParaphrase for article {article_id}")
    from service.ai_core.platform import get_ai_tool

    tool = get_ai_tool("smart_paraphrase")
    res = tool.run({
        "highlighted_text": highlighted_text,
        "paragraph_text": paragraph_text,
        "start_idx": start_idx,
        "end_idx": end_idx,
    })

    result = res.output if isinstance(res.output, dict) else {}
    expanded_text = result.get("expanded_text", highlighted_text)
    paraphrased_text = result.get("paraphrased_text", highlighted_text)

    # Re-locate expanded_text position in paragraph
    new_start = paragraph_text.find(expanded_text)
    if new_start == -1:
        new_start = start_idx
        new_end = end_idx
        expanded_text = highlighted_text
    else:
        new_end = new_start + len(expanded_text)

    paraphrase_data = {
        "article_id": article_id,
        "paragraph_hash": paragraph_hash,
        "user_highlighted_text": highlighted_text,
        "user_start_index": start_idx,
        "user_end_index": end_idx,
        "original_expanded_text": expanded_text,
        "paraphrased_text": paraphrased_text,
        "start_index": new_start,
        "end_index": new_end,
    }
    return {"paraphrase_data": paraphrase_data}


@job("save_paraphrase", inputs=["paraphrase_data"])
def save_paraphrase(paraphrase_data: dict):
    """Persist new paraphrase to cache (skip if it already has an _id)."""
    content_repo = ContentRepository()
    if paraphrase_data and "_id" not in paraphrase_data and "id" not in paraphrase_data:
        content_repo.save_paraphrase(paraphrase_data)
    return {}
