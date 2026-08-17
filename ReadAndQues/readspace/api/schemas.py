"""
Pydantic schemas for ReadAndQues typed API endpoints.
"""

from typing import Any, Dict, List, Optional
from ninja import Schema


class StatusResponse(Schema):
    status: str
    message: Optional[str] = None


class ExamSubmitIn(Schema):
    score: int = 0
    total_questions: int = 0
    answers: Dict[str, Any] = {}
    highlighted_markdown: str = ""
    elapsed_time: int = 0


class ExamSubmitOut(Schema):
    status: str = "success"
    id: str
    related_articles: List[Dict[str, Any]] = []


class SmartParaphraseIn(Schema):
    paragraph_text: str
    start_index: int = 0
    end_index: int = 0


class SmartParaphraseOut(Schema):
    status: str = "success"
    paraphrased_text: Optional[str] = None
    explanation: Optional[str] = None


class SaveMarkersIn(Schema):
    highlighted_markdown: str = ""


class PassageProofOut(Schema):
    status: str = "success"
    proof: Dict[str, Any]


class ArticleStatusOut(Schema):
    id: str
    stage: str
    ai_status: str
    has_quiz: bool
    has_passage_proof: bool
    title: Optional[str] = None


class SearchResultItem(Schema):
    article_id: Optional[str] = None
    id: Optional[str] = None
    title: str = ""
    source: Optional[str] = None
    theme: Optional[str] = None
    genre: Optional[str] = None
    word_count: Optional[int] = 0
    reading_time: Optional[int] = 0


class SearchResponseOut(Schema):
    status: str = "success"
    results: List[Dict[str, Any]] = []


class GenericAiToolIn(Schema):
    question: Optional[str] = None
    article_id: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
