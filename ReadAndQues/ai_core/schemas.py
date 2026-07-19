from datetime import datetime
from typing import Any, List, Optional, Dict
from typing_extensions import TypedDict

from pydantic import BaseModel, Field

class GraphState(TypedDict):
    """"
    For GraphState of Langgraph
    """
    original_text: str
    exam_config: Dict[str, Any]
    final_exam: Dict[str, Any]

from articles.models import QuizItem


class ExamOutput(BaseModel):
    quizzes: List[QuizItem]


