"""
database/Chroma/rag_operations.py — Operations for RAG Chunking, Indexing & Hybrid Retrieval
"""

import logging
import re
from typing import Dict, List, Optional

from database.BM25.operations import search_bm25
from database.BM25.text_preprocessing import process_text_to_tokens
from .connection import news_chunks_collection

logger = logging.getLogger(__name__)


class RecursiveTextSplitter:

    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                if len(para) > self.chunk_size:
                    sentences = re.split(r"(?<=[.!?]) +", para)
                    sub_chunk = ""
                    for sent in sentences:
                        if len(sub_chunk) + len(sent) + 1 <= self.chunk_size:
                            sub_chunk = f"{sub_chunk} {sent}".strip()
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = sent
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        if self.chunk_overlap > 0 and len(chunks) > 1:
            overlapped_chunks = []
            for i, c in enumerate(chunks):
                if i > 0:
                    overlap_prefix = chunks[i - 1][-self.chunk_overlap :]
                    c = f"{overlap_prefix}... {c}"
                overlapped_chunks.append(c)
            return overlapped_chunks

        return chunks


_text_splitter = RecursiveTextSplitter(
    chunk_size=1500,
    chunk_overlap=200,
)



def chunk_article_text(full_text: str) -> List[str]:
    """Split article full_text into readable chunks preserving paragraph context."""
    if not full_text:
        return []
    chunks = _text_splitter.split_text(full_text)
    return [c.strip() for c in chunks if c.strip()]


def upsert_article_chunks(
    article_id: str,
    title: str,
    full_text: str,
    url: str = "",
    theme: str = "General",
    genre: str = "general",
    published_at: str = "",
) -> bool:
    """
    Chunk article full_text and upsert into ChromaDB `news_chunks` collection.
    """
    if not news_chunks_collection or not full_text or not article_id:
        return False

    try:
        chunks = chunk_article_text(full_text)
        if not chunks:
            return False

        # First clean up any old chunks for this article_id
        try:
            news_chunks_collection.delete(where={"article_id": str(article_id)})
        except Exception:
            pass  # Delete may fail if no existing records match

        documents = []
        metadatas = []
        ids = []

        total_chunks = len(chunks)
        for idx, chunk_text in enumerate(chunks):
            chunk_id = f"{article_id}_chunk_{idx}"
            metadata = {
                "article_id": str(article_id),
                "title": title or "Untitled News",
                "url": url or "",
                "theme": theme or "General",
                "genre": genre or "general",
                "published_at": published_at or "",
                "chunk_index": idx,
                "total_chunks": total_chunks,
            }
            documents.append(chunk_text)
            metadatas.append(metadata)
            ids.append(chunk_id)

        news_chunks_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"[RAG] Indexed {total_chunks} chunks for article {article_id}")
        return True
    except Exception as e:
        logger.error(f"[RAG] Failed to upsert chunks for article {article_id}: {e}")
        return False


def vector_search_chunks(
    query: str, limit: int = 10, where_filter: Optional[Dict] = None
) -> List[Dict]:
    """Perform vector similarity search on ChromaDB news_chunks."""
    if not news_chunks_collection or not query:
        return []

    try:
        kwargs = {"query_texts": [query], "n_results": limit}
        if where_filter:
            kwargs["where"] = where_filter

        results = news_chunks_collection.query(**kwargs)
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        hits = []
        for i in range(len(results["ids"][0])):
            doc_id = results["ids"][0][i]
            document = results["documents"][0][i] if "documents" in results and results["documents"] else ""
            metadata = results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else {}
            distance = results["distances"][0][i] if "distances" in results and results["distances"] else 0.0

            hits.append({
                "id": str(doc_id),
                "text": document,
                "metadata": metadata,
                "distance": distance,
                "score": 1.0 / (1.0 + distance),  # Convert distance to score
            })

        return hits
    except Exception as e:
        logger.error(f"[RAG] Vector search error: {e}")
        return []


def hybrid_search_chunks(
    query: str, top_k: int = 6, where_filter: Optional[Dict] = None
) -> List[Dict]:
    """
    Hybrid Search combining ChromaDB Vector Search + BM25 Keyword Search
    using Reciprocal Rank Fusion (RRF).
    """
    if not query:
        return []

    # 1. Vector Search
    vector_hits = vector_search_chunks(query, limit=top_k * 2, where_filter=where_filter)

    # 2. BM25 Search
    tokens = process_text_to_tokens(query)
    bm25_raw_hits = search_bm25(tokens, n=top_k * 2) if tokens else []

    # RRF Scoring Map: doc_key -> {"score": float, "hit": dict}
    rrf_map: Dict[str, Dict] = {}
    rrf_k = 60.0

    # Process vector hits
    for rank, hit in enumerate(vector_hits):
        doc_key = hit["id"]
        rrf_score = 1.0 / (rrf_k + (rank + 1))
        rrf_map[doc_key] = {
            "rrf_score": rrf_score,
            "hit": hit,
            "sources": ["vector"],
        }

    # Process BM25 hits
    for rank, hit in enumerate(vector_hits if not bm25_raw_hits else bm25_raw_hits):
        if not bm25_raw_hits:
            break
        article_id = hit["id"]

        # Find corresponding vector hit if already retrieved
        matching_key = None
        for key in rrf_map:
            if rrf_map[key]["hit"]["metadata"].get("article_id") == article_id:
                matching_key = key
                break

        rrf_score = 1.0 / (rrf_k + (rank + 1))

        if matching_key:
            rrf_map[matching_key]["rrf_score"] += rrf_score
            rrf_map[matching_key]["sources"].append("bm25")
        else:
            synthetic_key = f"{article_id}_bm25_{rank}"
            rrf_map[synthetic_key] = {
                "rrf_score": rrf_score,
                "hit": {
                    "id": synthetic_key,
                    "text": "",
                    "metadata": {"article_id": article_id, "title": f"Article {article_id}"},
                    "distance": 1.0,
                    "score": hit.get("score", 0.0),
                },
                "sources": ["bm25"],
            }

    # Sort candidates by combined RRF score descending
    sorted_candidates = sorted(
        rrf_map.values(), key=lambda x: x["rrf_score"], reverse=True
    )

    final_results = []
    for candidate in sorted_candidates[:top_k]:
        hit = candidate["hit"]
        hit["rrf_score"] = round(candidate["rrf_score"], 4)
        hit["retrieval_sources"] = candidate["sources"]
        final_results.append(hit)

    return final_results
