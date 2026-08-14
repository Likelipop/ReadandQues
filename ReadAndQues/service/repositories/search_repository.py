"""
service/repositories/search_repository.py — Unified search interface.

Consolidates BM25 keyword search and ChromaDB semantic search behind
a single repository. Handles text chunking and RRF hybrid ranking.
Protected by @db_safe error boundary.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from database.BM25.connection import get_index, rebuild_index
from database.BM25.operations import search_bm25, find_related_by_markers
from database.BM25.text_preprocessing import process_text_to_tokens
from database.Chroma.operations import add_article_vector, search_by_text, query_related_chroma_ids
from database.Chroma.rag_operations import upsert_article_chunks, vector_search_chunks
from database.Mongo.article_index import get_article_index
from service.repositories.utils import db_safe

logger = logging.getLogger(__name__)


class RecursiveTextSplitter:
    """Helper for splitting full article text into readable chunks."""

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


_text_splitter = RecursiveTextSplitter()


@dataclass
class SearchResult:
    """Standardized search result returned by all search methods."""
    article_id: str
    title: str = ""
    source: str = ""
    snippet: str = ""
    date: str = ""
    score: float = 0.0
    similarity: Optional[int] = None
    metadata: Dict = field(default_factory=dict)


class SearchRepository:
    """Unified search interface — BM25 keyword + ChromaDB semantic."""

    # ── Keyword Search ────────────────────────────────────────────────────

    @db_safe(default_return=[])
    def search_keyword(self, query: str, limit: int = 10) -> List[SearchResult]:
        results = []
        seen_ids = set()

        tokens = process_text_to_tokens(query)
        if tokens:
            bm25_hits = search_bm25(tokens, n=limit)
            for hit in bm25_hits:
                article_id = hit["id"]
                doc = get_article_index(article_id)
                if doc:
                    date_val = doc.get("published_at", doc.get("created_at", ""))
                    date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else ""
                    results.append(SearchResult(
                        article_id=str(doc["_id"]),
                        title=doc.get("title", "No Title"),
                        source=doc.get("source_name", "Unknown"),
                        date=date_str,
                        score=hit.get("score", 0.0),
                    ))
                    seen_ids.add(str(doc["_id"]))

        # Fallback / supplementary MongoDB regex search for partial matches
        if len(results) < limit:
            from database.Mongo.article_index import search_article_index_by_text
            mongo_docs = search_article_index_by_text(query, limit=limit - len(results))
            for doc in mongo_docs:
                aid = str(doc["_id"])
                if aid not in seen_ids:
                    date_val = doc.get("published_at", doc.get("created_at", ""))
                    date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else ""
                    results.append(SearchResult(
                        article_id=aid,
                        title=doc.get("title", "No Title"),
                        source=doc.get("source_name", "Unknown"),
                        date=date_str,
                        score=0.5,
                    ))
                    seen_ids.add(aid)

        return results

    # ── Semantic Search ───────────────────────────────────────────────────

    @db_safe(default_return=[])
    def search_semantic(self, query: str, limit: int = 5) -> List[SearchResult]:
        hits = search_by_text(query, limit=limit)
        results = []
        for hit in hits:
            article_id = hit["id"]
            doc = get_article_index(article_id)
            if doc:
                distance = float(hit.get("distance", 0.0))
                similarity = max(0, min(100, int((1.0 - distance / 2.0) * 100)))
                metadata = hit.get("metadata", {})
                date_val = doc.get("published_at", doc.get("created_at", ""))
                date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else ""
                results.append(SearchResult(
                    article_id=str(doc["_id"]),
                    title=doc.get("title", metadata.get("title", "No Title")),
                    source=doc.get("source_name", "Unknown"),
                    date=date_str,
                    similarity=similarity,
                    score=1.0 - distance / 2.0,
                ))

        if not results:
            return self.search_keyword(query, limit=limit)

        return results

    # ── Hybrid Search (Reciprocal Rank Fusion) ────────────────────────────

    @db_safe(default_return=[])
    def search_hybrid(
        self, query: str, top_k: int = 6, where_filter: Optional[Dict] = None
    ) -> List[Dict]:
        """Hybrid Search combining ChromaDB Vector Search + BM25 Lexical via RRF."""
        if not query:
            return []

        # 1. Vector Search
        vector_hits = vector_search_chunks(query, limit=top_k * 2, where_filter=where_filter)

        # 2. BM25 Search
        tokens = process_text_to_tokens(query)
        bm25_raw_hits = search_bm25(tokens, n=top_k * 2) if tokens else []

        rrf_map: Dict[str, Dict] = {}
        rrf_k = 60.0

        for rank, hit in enumerate(vector_hits):
            doc_key = hit["id"]
            rrf_score = 1.0 / (rrf_k + (rank + 1))
            rrf_map[doc_key] = {
                "rrf_score": rrf_score,
                "hit": hit,
                "sources": ["vector"],
            }

        for rank, hit in enumerate(vector_hits if not bm25_raw_hits else bm25_raw_hits):
            if not bm25_raw_hits:
                break
            article_id = hit["id"]

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

    @db_safe(default_return=[])
    def search_vector_chunks(
        self, query: str, limit: int = 10, where_filter: Optional[Dict] = None
    ) -> List[Dict]:
        return vector_search_chunks(query, limit=limit, where_filter=where_filter)

    # ── Related Articles ──────────────────────────────────────────────────

    @db_safe(default_return=[])
    def find_related_by_summary(
        self, summary: str, exclude_id: str, limit: int = 5
    ) -> List[str]:
        return query_related_chroma_ids(summary, exclude_id=exclude_id, limit=limit)

    @db_safe(default_return=[])
    def find_related_by_highlights(
        self, highlighted_markdown: str, exclude_id: Optional[str] = None, n: int = 5
    ) -> List[Dict]:
        return find_related_by_markers(highlighted_markdown, exclude_id=exclude_id, n=n)

    # ── Indexing ──────────────────────────────────────────────────────────

    @db_safe(default_return=False)
    def index_article_vector(
        self,
        article_id: str = "",
        summary: str = "",
        title: str = "",
        url: str = "",
        theme: str = "General",
        genre: str = "general",
        gold_id: Optional[str] = None,
    ) -> bool:
        aid = gold_id or article_id
        return add_article_vector(aid, summary, title, url, theme, genre)

    @db_safe(default_return=False)
    def index_article_chunks(
        self,
        article_id: str,
        title: str,
        full_text: str,
        url: str = "",
        theme: str = "General",
        genre: str = "general",
        published_at: str = "",
    ) -> bool:
        chunks = _text_splitter.split_text(full_text)
        if not chunks:
            return False
        return upsert_article_chunks(
            article_id, title, full_text, url, theme, genre, published_at
        )

    @db_safe(default_return=None)
    def rebuild_keyword_index(self) -> None:
        rebuild_index()

    def tokenize_query(self, query: str) -> List[str]:
        return process_text_to_tokens(query)
