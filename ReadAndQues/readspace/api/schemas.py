"""
Pydantic schemas for ReadAndQues typed API endpoints.
"""

from typing import Any

from ninja import Schema


class StatusResponse(Schema):
    status: str
    message: str | None = None


class ExamSubmitIn(Schema):
    score: int = 0
    total_questions: int = 0
    answers: dict[str, Any] = {}
    highlighted_markdown: str = ""
    elapsed_time: int = 0


class ExamSubmitOut(Schema):
    status: str = "success"
    id: str
    related_articles: list[dict[str, Any]] = []


class SmartParaphraseIn(Schema):
    paragraph_text: str
    start_index: int = 0
    end_index: int = 0


class SmartParaphraseOut(Schema):
    status: str = "success"
    paraphrased_text: str | None = None
    explanation: str | None = None


class SaveMarkersIn(Schema):
    highlighted_markdown: str = ""


class PassageProofOut(Schema):
    status: str = "success"
    proof: dict[str, Any]


class ArticleStatusOut(Schema):
    id: str
    stage: str
    ai_status: str
    has_quiz: bool
    has_passage_proof: bool
    title: str | None = None


class SearchResultItem(Schema):
    article_id: str | None = None
    id: str | None = None
    title: str = ""
    source: str | None = None
    theme: str | None = None
    genre: str | None = None
    word_count: int | None = 0
    reading_time: int | None = 0


class SearchResponseOut(Schema):
    status: str = "success"
    results: list[dict[str, Any]] = []


class GenericAiToolIn(Schema):
    question: str | None = None
    article_id: str | None = None
    input_data: dict[str, Any] | None = None
