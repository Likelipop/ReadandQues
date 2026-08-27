"""
service/infrastructure/chroma/chunking.py — Parent-Child Chunking algorithm for RAG.

Strategy:
- Parent Chunks: ~500 words (group of paragraphs)
- Child Chunks: Individual paragraphs within parent
"""

from typing import Any


def chunk_article_with_hierarchy(
    article_id: str,
    full_text: str,
    title: str = "",
    url: str = "",
    theme: str = "General",
    genre: str = "general",
    published_at: str = "",
    target_parent_words: int = 500,
) -> list[dict[str, Any]]:
    """
    Splits full text into parent-child chunks for ChromaDB indexing.
    Returns a list of dicts with: {id, text, metadata}.
    """
    if not full_text or not full_text.strip():
        return []

    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks_to_index = []
    parent_index = 0
    child_index_in_parent = 0

    current_parent_paragraphs = []
    current_parent_words = 0

    def _flush_parent(paras: list[str], p_idx: int) -> str:
        parent_text = "\n\n".join(paras)
        parent_id = f"{article_id}_parent_{p_idx}"
        chunks_to_index.append(
            {
                "id": parent_id,
                "text": parent_text,
                "metadata": {
                    "article_id": str(article_id),
                    "title": title or "Untitled",
                    "url": url or "",
                    "theme": theme or "General",
                    "genre": genre or "general",
                    "published_at": published_at or "",
                    "chunk_type": "parent",
                    "parent_index": p_idx,
                    "child_count": len(paras),
                },
            }
        )
        return parent_id

    # Build parent and child chunks
    parent_id = f"{article_id}_parent_{parent_index}"

    for p in paragraphs:
        p_words = len(p.split())
        if current_parent_words + p_words > target_parent_words and current_parent_paragraphs:
            parent_id = _flush_parent(current_parent_paragraphs, parent_index)
            parent_index += 1
            current_parent_paragraphs = []
            current_parent_words = 0
            child_index_in_parent = 0

        current_parent_paragraphs.append(p)
        current_parent_words += p_words

        # Add child chunk
        child_id = f"{article_id}_child_{parent_index}_{child_index_in_parent}"
        chunks_to_index.append(
            {
                "id": child_id,
                "text": p,
                "metadata": {
                    "article_id": str(article_id),
                    "title": title or "Untitled",
                    "url": url or "",
                    "theme": theme or "General",
                    "genre": genre or "general",
                    "published_at": published_at or "",
                    "chunk_type": "child",
                    "parent_id": parent_id,
                    "parent_index": parent_index,
                    "child_index": child_index_in_parent,
                },
            }
        )
        child_index_in_parent += 1

    if current_parent_paragraphs:
        _flush_parent(current_parent_paragraphs, parent_index)

    return chunks_to_index
