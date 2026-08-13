import hashlib
import re
from typing import List
from pydantic import BaseModel


class ArticleChunk(BaseModel):
    chunk_id: str
    text: str
    start_offset: int
    end_offset: int
    content_hash: str


def chunk_article_text(article_text: str) -> List[ArticleChunk]:
    """
    Splits article text into stable, offset-aware chunks with SHA-256 hashes.
    """
    if not article_text or not article_text.strip():
        return []

    paragraphs = [p for p in re.split(r"\n\s*\n", article_text) if p.strip()]
    chunks = []
    current_pos = 0

    for idx, p in enumerate(paragraphs):
        p_clean = p.strip()
        start = article_text.find(p_clean, current_pos)
        if start == -1:
            start = current_pos
        end = start + len(p_clean)
        current_pos = end

        c_hash = hashlib.sha256(p_clean.encode("utf-8")).hexdigest()[:16]
        chunks.append(
            ArticleChunk(
                chunk_id=f"chunk_{idx}",
                text=p_clean,
                start_offset=start,
                end_offset=end,
                content_hash=c_hash,
            )
        )

    return chunks
