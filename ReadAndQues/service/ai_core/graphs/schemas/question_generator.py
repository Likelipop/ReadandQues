"""
service/ai_core/graphs/schemas/question_generator.py — Clean, unified Pydantic schemas for question generation.
"""

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class QuizItem(BaseModel):
    quiz_type: str = Field(..., description="Question type: multiple_choice, yes_no_notgiven, or fill_in_blank")
    question: str = Field(..., description="The question text or summary paragraph with blanks [1]..[5]")
    options: list[str] | None = Field(default=None, description="Options for multiple choice questions, or null")
    correct_answer: str = Field(..., description="Correct answer text")
    explanation: str = Field(default="", description="Educational explanation for why the answer is correct")
    supporting_text: str = Field(default="", description="Exact sentence(s) from the text supporting the answer")
    source_chunk_ids: list[str] | None = Field(default=None, description="Chunk IDs related to this quiz")
    reading_skill: str | None = Field(default=None, description="Reading skill tested (e.g. inference, main_idea)")


class SemanticAnalysis(BaseModel):
    genre: str = Field(
        default="general", description="Passage genre: narrative, poetry, scientific, persuasive, general"
    )
    theme: str = Field(default="General", description="Primary theme category: Science, Technology, Society, etc.")
    summary: str = Field(default="", description="Concise 2-3 sentence summary of the passage")
    core: dict[str, Any] = Field(default_factory=dict, description="Detailed core analysis dictionary")


class ExamOutput(BaseModel):
    quizzes: list[QuizItem] = Field(default_factory=list, description="List of generated quiz questions")
    semantic_analysis: SemanticAnalysis | None = Field(default=None, description="Extracted semantic metadata")


class GraphState(TypedDict, total=False):
    original_text: str
    semantic_analysis: dict[str, Any]
    exam_config: dict[str, Any]
    raw_quizzes: list[dict[str, Any]]
    verified_quizzes: list[dict[str, Any]]
    final_exam: dict[str, Any]
