import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from service.domain.enums import AIStatus, ArticleStage, ArticleStatus, MedallionStage, ThemeCategory


# ── Path Helpers ──────────────────────────────────────────────────────────────

def generate_article_id(url: Optional[str] = None) -> str:
    """
    Generates a stable, canonical article identifier.
    If a URL is provided, derives a deterministic ID from the URL hash (SHA-256).
    Otherwise, generates a unique prefix-based UUID string.
    """
    if url and url.strip():
        url_hash = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]
        return f"art_{url_hash}"
    return f"art_{uuid.uuid4().hex[:16]}"


def minio_bronze_prefix(article_id: str) -> str:
    """Returns the MinIO bronze path prefix for a given article_id."""
    return f"bronze/{article_id}"


def minio_silver_prefix(article_id: str) -> str:
    """Returns the MinIO silver path prefix for a given article_id."""
    return f"silver/{article_id}"


def minio_gold_prefix(article_id: str) -> str:
    """Returns the MinIO gold path prefix for a given article_id."""
    return f"gold/{article_id}"


# ── New Clean Contracts ───────────────────────────────────────────────────────

class ArticleIndexContract(BaseModel):
    """
    Lightweight index document stored in MongoDB `article_index` collection.
    _id = article_id. Contains only metadata needed for listing/status checks.
    Full content (text, HTML, AI results) lives in MinIO.
    """
    article_id: str
    url: str
    title: str = ""
    source_name: str = ""
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None
    stage: ArticleStage = ArticleStage.BRONZE
    ai_status: AIStatus = AIStatus.PENDING_GENERATION
    error_message: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExamDocContract(BaseModel):
    """
    AI-generated exam document stored in MongoDB `exams` collection.
    article_id is the foreign key to article_index.
    Full enriched JSON (analysis + exams) also mirrored to MinIO gold/.
    """
    article_id: str
    theme: str = ThemeCategory.GENERAL.value
    genre: str = "general"
    summary: str = ""
    analysis: Dict[str, Any] = Field(default_factory=dict)
    exams: List[Dict[str, Any]] = Field(default_factory=list)
    word_count: int = 0
    language: str = "en"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Quiz & Exam Contracts (unchanged) ────────────────────────────────────────

class QuizOptionContract(BaseModel):
    id: str
    text: str


class QuizItemContract(BaseModel):
    id: str
    question_type: str
    question: str
    options: List[QuizOptionContract] = Field(default_factory=list)
    correct_answer: Any
    explanation: Optional[str] = ""


class ExamContract(BaseModel):
    exam_id: str
    title: Optional[str] = ""
    quizzes: List[QuizItemContract] = Field(default_factory=list)


class SmartParaphraseContract(BaseModel):
    selected_text: str
    surrounding_context: Optional[str] = ""
    expanded_text: Optional[str] = ""
    paraphrased_text: str
    start_index: int = 0
    end_index: int = 0


# ── Legacy Contract (kept for backward compat during migration) ───────────────

class ArticleContract(BaseModel):
    """
    Legacy contract — still used by ArticleRepository and readspace views.
    Will be removed after Phase 7 migration is complete.
    """
    article_id: str
    url: str
    title: str = "Loading title..."
    original_text: str = ""
    cleaned_text: Optional[str] = ""
    summary: Optional[str] = ""
    theme: str = ThemeCategory.GENERAL.value
    genre: str = "general"
    status: ArticleStatus = ArticleStatus.CRAWLING
    ai_status: AIStatus = AIStatus.PENDING_GENERATION
    user_id: int = 0
    exams: List[ExamContract] = Field(default_factory=list)
    smart_paraphrases: List[SmartParaphraseContract] = Field(default_factory=list)
    error_message: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExamAttemptContract(BaseModel):
    attempt_id: Optional[str] = None
    user_id: int
    article_id: str
    score: int = 0
    total_questions: int = 0
    answers: Dict[str, Any] = Field(default_factory=dict)
    highlighted_markdown: Optional[str] = ""
    elapsed_time: int = 0
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RawSourceManifestContract(BaseModel):
    manifest_version: str = "1.0"
    article_id: str
    url: str
    sha256_hash: str
    raw_size_bytes: int
    stage: MedallionStage = MedallionStage.BRONZE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
