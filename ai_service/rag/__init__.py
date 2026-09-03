"""
ai_service/rag — Complete RAG subsystem (Router, Grounding, Search, Agents).
"""
from ai_service.rag.pipeline import execute_rag_pipeline, get_rag_router
from ai_service.rag.schemas import Citation, RAGQuery, RAGResponse

__all__ = [
    "execute_rag_pipeline",
    "get_rag_router",
    "Citation",
    "RAGQuery",
    "RAGResponse",
]
