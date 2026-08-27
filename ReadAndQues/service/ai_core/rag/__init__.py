"""
service/ai_core/rag — Centralized RAG Router and Retrieval Agents.
"""

from .agents.news.agent import run_news_agent
from .router import build_rag_router_graph, execute_rag_pipeline, get_rag_router
from .schemas import AgentResult, Citation, RAGResponse

__all__ = [
    "execute_rag_pipeline",
    "get_rag_router",
    "build_rag_router_graph",
    "run_news_agent",
    "RAGResponse",
    "Citation",
    "AgentResult",
]
