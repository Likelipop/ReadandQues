from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class QuizItem(BaseModel):
    quiz_type: str = Field(
        ..., description="yes_no_notgiven or fill_in_blank"
    )
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    supporting_text: str = Field(
        ..., description="Verbatim sentence from the article"
    )


class Exam(BaseModel):
    exam_id: str
    title: str = "IELTS Academic Reading Test"
    total_questions: int
    quizzes: List[QuizItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ArticleMongoModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    url: str
    title: str
    original_text: str
    source_name: Optional[str] = "Unknown"
    exams: List[Exam] = Field(default_factory=list)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }