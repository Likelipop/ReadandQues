"""
ai_service/rag/grounding — Semantic Chunking, Reranking, Retrieval, and Passage Proof.
"""
from ai_service.rag.grounding.chunking import ArticleChunk, chunk_article_text
from ai_service.rag.grounding.passage_proof import get_passage_proof
from ai_service.rag.grounding.reranker import rerank_chunks
from ai_service.rag.grounding.retrieval import retrieve_article_chunks

__all__ = [
    "ArticleChunk",
    "chunk_article_text",
    "get_passage_proof",
    "rerank_chunks",
    "retrieve_article_chunks",
]
