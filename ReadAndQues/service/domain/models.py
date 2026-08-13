"""
service/domain/models.py — Pure Domain Models for ReadAndQues.

Zen design: Minimalist, clear names, zero redundant suffixes, single source of truth.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── 1. Path & ID Helpers ──────────────────────────────────────────────────────

def generate_article_id(url: Optional[str] = None) -> str:
    """
    Generates a stable, canonical article identifier.
    If a URL is provided, derives a deterministic ID from SHA-256(url).
    """
    if url and url.strip():
        url_hash = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]
        return f"art_{url_hash}"
    return f"art_{uuid.uuid4().hex[:16]}"


def minio_bronze_prefix(article_id: str) -> str:
    return f"bronze/{article_id}"


def minio_silver_prefix(article_id: str) -> str:
    return f"silver/{article_id}"


def minio_gold_prefix(article_id: str) -> str:
    return f"gold/{article_id}"


# ── 2. Enums ──────────────────────────────────────────────────────────────────

class Stage(str, Enum):
    """Medallion storage layer stage."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class Status(str, Enum):
    """Pipeline processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    # Backward compatibility aliases
    CRAWLING = "pending"
    IN_PROGRESS = "processing"
    PENDING_GENERATION = "pending"


class ThemeCategory(str, Enum):
    GENERAL = "General"
    ECONOMY = "Economy"
    SOCIETY = "Society"
    EDUCATION = "Education"
    TECHNOLOGY = "Technology"
    SCIENCE = "Science"
    ENVIRONMENT = "Environment"
    CULTURE = "Culture"
    HEALTH = "Health"


# ── 3. Exam & Quiz Models ─────────────────────────────────────────────────────

class Option(BaseModel):
    """A quiz option."""
    id: str
    text: str


class Question(BaseModel):
    """A quiz question item."""
    id: str
    question_type: str = "single_choice"
    question: str
    options: List[Option] = Field(default_factory=list)
    correct_answer: Any = ""
    explanation: Optional[str] = ""


class Exam(BaseModel):
    """An exam containing a set of quiz questions."""
    exam_id: str = ""
    title: Optional[str] = ""
    quizzes: List[Question] = Field(default_factory=list)


class Paraphrase(BaseModel):
    """Smart paraphrase result."""
    selected_text: str
    surrounding_context: Optional[str] = ""
    expanded_text: Optional[str] = ""
    paraphrased_text: str
    start_index: int = 0
    end_index: int = 0


# ── 4. Core Article Model ─────────────────────────────────────────────────────

class Article(BaseModel):
    """
    Single unified model representing an Article across the entire application.
    Replaces ArticleIndexContract, ExamDocContract, and ArticleContract.
    """
    article_id: str
    id: str = ""  # Alias for article_id for UI template compatibility
    url: str
    title: str = "Loading title..."
    source_name: str = "Unknown"
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None

    # Status & Progress
    stage: Stage = Stage.BRONZE
    status: Status = Status.PENDING
    error_message: Optional[str] = ""

    # AI Enriched Fields
    theme: str = ThemeCategory.GENERAL.value
    genre: str = "general"
    summary: str = ""
    original_text: str = ""
    cleaned_text: Optional[str] = ""
    word_count: int = 0
    language: str = "en"
    user_id: int = 0
    exams: List[Exam] = Field(default_factory=list)
    smart_paraphrases: List[Paraphrase] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context: Any) -> None:
        """Ensure id alias is always populated from article_id."""
        if not self.id and self.article_id:
            self.id = self.article_id


# ── 5. User Interaction Models ────────────────────────────────────────────────

class ExamAttempt(BaseModel):
    """User's exam attempt submission."""
    attempt_id: Optional[str] = None
    user_id: int
    article_id: str
    score: int = 0
    total_questions: int = 0
    answers: Dict[str, Any] = Field(default_factory=dict)
    highlighted_markdown: Optional[str] = ""
    elapsed_time: int = 0
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RawSourceManifest(BaseModel):
    """SHA-256 Manifest for raw crawled content in MinIO Bronze."""
    manifest_version: str = "1.0"
    article_id: str
    url: str
    sha256_hash: str
    raw_size_bytes: int
    stage: Stage = Stage.BRONZE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
