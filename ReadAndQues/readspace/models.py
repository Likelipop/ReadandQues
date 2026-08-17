from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# Create your models here.

# ==========================================
# 1. QUIZ ITEM — Align with ai_core/schemas.py
# ==========================================
class QuizItem(BaseModel):
    """
    Standard schema for a single quiz item saved to MongoDB.
    Supports two types:
      - yes_no_not_given : Yes/No/Not Given
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
    options: list[str] | None = Field(
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
    explanation: str | None = Field(
        default="", description="Detailed explanation of why the answer is correct."
    )
    supporting_text: str | None = Field(
        default="",
        description="Verbatim sentence(s) from the article supporting the answer.",
    )
    reading_skill: str | None = Field(
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
    id: str | None = Field(default=None, alias="_id")

    url: str = Field(..., description="Original article URL")
    title: str = Field(..., description="Article title")
    original_text: str = Field(..., description="Raw crawled content")
    html_content: str | None = Field(
        default=None, description="Raw HTML for rendering in UI"
    )
    clean_text: str | None = Field(
        default=None, description="Cleaned text (after Smart Cleaner)"
    )
    source_name: str | None = Field(
        default="Unknown", description="Source name, e.g., BBC, CNN"
    )

    # Exam configuration used during generation (for auditing/re-generating)
    exam_config: dict[str, Any] | None = Field(
        default=None, description='Generation config, e.g., {"total_questions": 10}'
    )

    # All questions (MCQ Yes/No/NG followed by FIB Summary Completion)
    quizzes: list[QuizItem] = Field(default_factory=list)

    # Generated exams (aligned with structure from Celery)
    exams: list[dict[str, Any]] = Field(default_factory=list)

    # Classification and images
    theme: str | None = Field(
        default=None, description="Article theme (e.g., Technology, Science)"
    )
    genre: str | None = Field(
        default=None, description="Text genre (e.g., scientific, news)"
    )
    image_url: str | None = Field(default=None, description="Main article image URL")
    image_urls: list[str] = Field(
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
    score: int = 0
    total_questions: int = 0
    answers: dict[str, Any] = {}
    highlighted_markdown: str = ""
    elapsed_time: int = 0
    submitted_at: datetime
