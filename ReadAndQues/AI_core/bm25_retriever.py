"""
AI_core/bm25_retriever.py

NLP pipeline: highlighted_markdown → clean → tokenize → lemmatize (spaCy)
→ BM25 query tokens.

spaCy model: en_core_web_sm (nhẹ, đủ dùng cho lemmatization + stopword removal)
"""
import re
import logging
import spacy
from database.BM25.operations import search_bm25

logger = logging.getLogger(__name__)

# ── Step 1: Extract marked text ───────────────────────────────────────────────

def extract_markers(highlighted_markdown: str) -> str:
    """
    Input:  "bình thường ==đoạn được highlight== tiếp tục ==đoạn khác=="
    Output: "đoạn được highlight đoạn khác"
    """
    if not highlighted_markdown:
        return ""
    marked_texts = re.findall(r"==([^=]+)==", highlighted_markdown)
    return " ".join(marked_texts)


# ── Public API ────────────────────────────────────────────────────────────────

def process_markers_to_tokens(highlighted_markdown: str) -> list[str]:
    """
    Full pipeline: highlighted_markdown → query tokens sẵn sàng cho BM25.
    """
    raw = extract_markers(highlighted_markdown)
    if not raw.strip():
        return []

    from database.BM25.text_preprocessing import process_text_to_tokens
    tokens = process_text_to_tokens(raw)

    logger.debug(f"[BM25Retriever] Markers extracted: '{raw[:80]}...'")
    logger.debug(f"[BM25Retriever] Tokens ({len(tokens)}): {tokens[:10]}")

    return tokens


def find_related_by_markers(
    highlighted_markdown: str,
    exclude_id: str,
    n: int = 5,
) -> list[dict]:
    """
    High-level API dùng cho service layer.

    Returns:
        [{"id": str, "score": float}, ...]
    """
    tokens = process_markers_to_tokens(highlighted_markdown)
    if not tokens:
        return []

    return search_bm25(tokens, n=n, exclude_id=exclude_id)
