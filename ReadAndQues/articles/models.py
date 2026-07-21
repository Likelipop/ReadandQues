"""
articles/models.py — MongoDB document schema layer.

All pure-Pydantic domain models (QuizItem, SemanticAnalysis, TokenUsageLog …)
are imported from ai_core.schemas — the Single Source of Truth.
This file only defines the MongoDB *document* wrappers that Django views use.
"""

from datetime import datetime
from typing import List, Optional

from django.db import models  # noqa: F401  (required for Django app registry)
from pydantic import BaseModel, Field

# ── Import canonical domain models from AI_core ───────
from AI_core.schemas import QuizItem, SemanticAnalysis, TokenUsageLog  # noqa: F401


__all__ = [
    "QuizItem",
    "SemanticAnalysis",
    "TokenUsageLog",
    "Exam",
    "ArticleMongoModel",
    "AttemptMongoModel",
]


# ==========================================
# EXAM  (embedded 1-to-N inside ArticleMongoModel)
# ==========================================

class Exam(BaseModel):
    exam_id: str = Field(
        ...,
        description="Globally unique exam identifier, format: EXAM_<12-char-uuid-hex>"
    )
    title: str = Field(default="IELTS Academic Reading Test")
    total_questions: int = Field(...)
    quizzes: List[QuizItem] = Field(default_factory=list)

    # Token usage per LangGraph node — production observability
    token_usage: List[TokenUsageLog] = Field(
        default_factory=list,
        description="Input/output token count logged per node for cost tracking"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==========================================
# ARTICLE MONGO DOCUMENT  (top-level collection)
# ==========================================

class ArticleMongoModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")

    # ── Raw content ─────────────────────────────────────────────────────────
    url:           str = Field(...)
    title:         str = Field(...)
    original_text: str = Field(...)
    source_name:   Optional[str] = Field(default="Unknown")
    image_url:     Optional[str] = Field(default=None, description="Main thumbnail/cover image hotlink")
    image_urls:    List[str] = Field(default_factory=list, description="List of hotlink image URLs extracted from article")

    theme:         Optional[str] = Field(default="General", description="Primary theme category (Economy, Society, Education, etc.)")
    genre:         Optional[str] = Field(default="general", description="Text genre (scientific, narrative, persuasive, etc.)")

    # ── AI-generated data ────────────────────────────────────────────────────
    # SemanticAnalysis produced by Node 1 (analyzer).
    # Optional so that documents in "pending" / "failed" status are still valid.
    analysis: Optional[SemanticAnalysis] = Field(
        default=None,
        description="Genre-aware semantic analysis from the analyzer node"
    )

    exams: List[Exam] = Field(default_factory=list)

    # ── Processing state ─────────────────────────────────────────────────────
    error_message: Optional[str] = Field(
        default=None,
        description="Set when status == 'failed'"
    )
    status: str = Field(
        default="pending",
        description="pending | completed | failed"
    )

    # ── Ownership ────────────────────────────────────────────────────────────
    user_id: Optional[int] = Field(
        default=None,
        description="Django User.id who imported this article"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
    }


# ==========================================
# ATTEMPT MONGO DOCUMENT
# ==========================================

class AttemptMongoModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: int = Field(...)
    article_id: str = Field(...)
    score: int = Field(...)
    total_questions: int = Field(...)
    answers: dict = Field(default_factory=dict, description="Dictionary of quiz ID to user's answer")
    highlighted_markdown: str = Field(..., description="The article text with ==highlights== markup")
    elapsed_time: int = Field(..., description="Time taken in seconds")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }