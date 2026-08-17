"""
service/rag/schemas.py — Pydantic Schemas for RAG Engine & Router.
"""

from typing import Any

from pydantic import BaseModel, Field

from service.domain.enums import AgentIntent


class Citation(BaseModel):
    """Citation metadata for grounded RAG answers."""
    article_id: str
    title: str
    url: str | None = ""
    theme: str | None = "General"
    genre: str | None = "general"
    rrf_score: float = 0.0


class RAGQuery(BaseModel):
    """Incoming user RAG query."""
    question: str
    article_id: str | None = None
    user_id: int | None = None
    conversation_id: str | None = None
    filters: dict[str, Any] | None = None


class AgentResult(BaseModel):
    """Execution output from a specialized RAG agent."""
    intent: AgentIntent
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks_count: int = 0
    confidence_score: float = 1.0
    execution_time_ms: float = 0.0
    model_used: str = "gpt-4o-mini"


class RAGResponse(BaseModel):
    """Final outer response returned to services/selectors layer."""
    status: str = "success"
    query: str
    intent: AgentIntent
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks_count: int = 0
    model_used: str = "gpt-4o-mini"
    error_message: str | None = ""
