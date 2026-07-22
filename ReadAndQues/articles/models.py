from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db import models
from pydantic import BaseModel, Field


# ==========================================
# 1. QUIZ ITEM — Align with ai_core/schemas.py
# ==========================================
class QuizItem(BaseModel):
    """
    Standard schema for a single quiz item saved to MongoDB.
    Supports two types:
      - yes_no_not_given : Yes/No/Not Given (IELTS Reading style)
      - fill_in_blank    : Summary Completion (5 blanks, answers separated by ' | ')
    """

    quiz_type: str = Field(
        ..., description="Question type: 'yes_no_not_given' or 'fill_in_blank'"
    )
    question: str = Field(
        ...,
        description=(
            "For yes_no_not_given: the statement to evaluate. "
            "For fill_in_blank: the summary paragraph containing [1]..[5]."
        ),
    )
    options: Optional[List[str]] = Field(
        default=None,
        description="For yes_no_not_given: ['Yes', 'No', 'Not Given']. For fill_in_blank: null.",
    )
    correct_answer: str = Field(
        ...,
        description=(
            "For yes_no_not_given: 'Yes', 'No', or 'Not Given'. "
            "For fill_in_blank: 5 answers separated by ' | ' (e.g. 'word1 | word2 | word3 | word4 | word5')."
        ),
    )
    explanation: Optional[str] = Field(
        default="", description="Detailed explanation of why the answer is correct."
    )
    supporting_text: Optional[str] = Field(
        default="",
        description="Verbatim sentence(s) from the article supporting the answer.",
    )
    reading_skill: Optional[str] = Field(
        default=None,
        description=(
            "Reading skill tested. One of: 'inference', 'main_idea', "
            "'author_purpose', 'detail', 'vocabulary_in_context'."
        ),
    )


# ==========================================
# 2. MAIN SCHEMA FOR MONGODB
# ==========================================
class ArticleMongoModel(BaseModel):
    """
    Main document stored in MongoDB 'articles' collection.

    Design considerations:
      - `analysis` is excluded to save storage since it's internal to the Mega Prompt.
      - `exam_config` is included to store exam configurations (e.g., number of questions).
      - `quizzes` contains all questions (MCQ + FIB) — aligned with ai_core/schemas.ExamOutput.
    """

    # PyMongo returns _id as ObjectId, mapping to str
    id: Optional[str] = Field(default=None, alias="_id")

    url: str = Field(..., description="Original article URL")
    title: str = Field(..., description="Article title")
    original_text: str = Field(..., description="Raw crawled content")
    clean_text: Optional[str] = Field(
        default=None, description="Cleaned text (after Smart Cleaner)"
    )
    source_name: Optional[str] = Field(
        default="Unknown", description="Source name, e.g., BBC, CNN"
    )

    # Exam configuration used during generation (for auditing/re-generating)
    exam_config: Optional[Dict[str, Any]] = Field(
        default=None, description='Generation config, e.g., {"total_questions": 10}'
    )

    # All questions (MCQ Yes/No/NG followed by FIB Summary Completion)
    quizzes: List[QuizItem] = Field(default_factory=list)

    # Generated exams (aligned with structure from Celery)
    exams: List[Dict[str, Any]] = Field(default_factory=list)

    # Classification and images
    theme: Optional[str] = Field(
        default=None, description="Article theme (e.g., Technology, Science)"
    )
    genre: Optional[str] = Field(
        default=None, description="Text genre (e.g., scientific, news)"
    )
    image_url: Optional[str] = Field(default=None, description="Main article image URL")
    image_urls: List[str] = Field(
        default_factory=list, description="List of all image URLs in the article"
    )

    # Pipeline metadata
    status: str = Field(
        default="pending",
        description="Status: pending | crawling | processing | completed | failed",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class AttemptMongoModel(BaseModel):
    user_id: int
    article_id: str
    score: int
    total_questions: int
    answers: Dict[str, Any]
    highlighted_markdown: str = ""
    elapsed_time: int = 0
    submitted_at: datetime
