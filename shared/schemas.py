"""Domain data models and schemas shared across Backend, AI Service, and Data Pipeline."""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def generate_article_id(url: str = "") -> str:
    """Generate a deterministic article ID from a URL using SHA-256."""
    if url and url.strip():
        url_hash = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]
        return f"art_{url_hash}"
    return f"art_{uuid.uuid4().hex[:16]}"


@dataclass
class Question:
    """A quiz question item."""
    type: str = "multiple_choice"
    question: str = ""
    options: list[str] = field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""
    supporting_quote: str = ""


@dataclass
class Exam:
    """An exam containing a collection of questions."""
    exam_id: str = ""
    title: str = ""
    questions: list[Question] = field(default_factory=list)


@dataclass
class Article:
    """An article containing metadata, text content, enriched details, keywords, and exams."""
    article_id: str = ""
    url: str = ""
    title: str = ""
    source_name: str = ""
    original_text: str = ""
    word_count: int = 0
    keywords: list[str] = field(default_factory=list)
    summary: str = ""
    exams: list[Exam] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = [
    "Article",
    "Exam",
    "Question",
    "generate_article_id",
]
