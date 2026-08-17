"""
pipeline/ai_core/schemas.py — Canonical Pydantic schema layer (SSOT).
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class TextGenre(str, Enum):
    narrative = "narrative"
    poetry = "poetry"
    scientific = "scientific"
    persuasive = "persuasive"
    general = "general"


class ThemeCategory(str, Enum):
    economy = "Economy"
    society = "Society"
    education = "Education"
    technology = "Technology"
    science = "Science"
    environment = "Environment"
    culture = "Culture"
    health = "Health"
    general = "General"


class CoreAnalysis(BaseModel):
    summary: str = Field(..., description="2–3 sentence summary of the main content")
    central_theme: str = Field(default="", description="Central theme / message")
    secondary_themes: list[str] = Field(default_factory=list)
    tone: str = Field(default="")
    tone_shifts: list[str] = Field(default_factory=list)
    structure_overview: str = Field(default="")
    key_terms: dict[str, str] = Field(default_factory=dict)
    likely_misunderstood: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    emotional_arc: str | None = Field(default=None)
    author_intent: str | None = Field(default=None)
    irrelevant_snippets: list[str] = Field(default_factory=list)


class NarrativeAnalysis(BaseModel):
    characters: dict[str, str] = Field(default_factory=dict)
    conflicts: list[str] = Field(default_factory=list)
    symbolism: list[str] = Field(default_factory=list)
    irony_or_foreshadowing: list[str] = Field(default_factory=list)
    narrative_perspective: str = Field(default="")
    unstated_implications: list[str] = Field(default_factory=list)


class PoetryAnalysis(BaseModel):
    imagery: list[str] = Field(default_factory=list)
    central_metaphor: str | None = Field(default=None)
    sound_devices: list[str] = Field(default_factory=list)
    form_structure: str = Field(default="")
    multiple_interpretations: list[str] = Field(default_factory=list)


class ScientificAnalysis(BaseModel):
    research_question: str = Field(default="")
    hypothesis: str | None = Field(default=None)
    methodology_summary: str = Field(default="")
    key_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    claims_vs_evidence: list[str] = Field(default_factory=list)
    terminology_glossary: dict[str, str] = Field(default_factory=dict)


class PersuasiveAnalysis(BaseModel):
    central_claim: str = Field(default="")
    supporting_arguments: list[str] = Field(default_factory=list)
    unstated_assumptions: list[str] = Field(default_factory=list)
    rhetorical_strategies: list[str] = Field(default_factory=list)
    counterarguments_addressed: list[str] = Field(default_factory=list)
    counterarguments_ignored: list[str] = Field(default_factory=list)
    bias_indicators: list[str] = Field(default_factory=list)


class SemanticAnalysis(BaseModel):
    genre: TextGenre
    theme: ThemeCategory = Field(default=ThemeCategory.general)
    core: CoreAnalysis
    narrative: NarrativeAnalysis | None = Field(default=None)
    poetry: PoetryAnalysis | None = Field(default=None)
    scientific: ScientificAnalysis | None = Field(default=None)
    persuasive: PersuasiveAnalysis | None = Field(default=None)

    model_config = {"use_enum_values": True}


class QuizItem(BaseModel):
    quiz_type: str = Field(...)
    question: str = Field(...)
    options: list[str] | None = Field(default=None)
    correct_answer: str = Field(...)
    explanation: str = Field(...)
    supporting_text: str = Field(...)
    source_chunk_ids: list[str] | None = Field(default=None)


class ExamOutput(BaseModel):
    quizzes: list[QuizItem]


class VerifierFeedback(BaseModel):
    passed: bool = Field(...)
    rejected_indices: list[int] = Field(default_factory=list)
    reason: str = Field(default="")


class TokenUsageLog(BaseModel):
    node: str
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)


class GraphState(TypedDict):
    original_text: str
    exam_config: dict[str, Any]
    semantic_analysis: dict[str, Any]
    raw_quizzes: list[dict[str, Any]]
    verified_quizzes: list[dict[str, Any]]
    retry_count: int
    token_log: list[dict[str, Any]]
    final_exam: dict[str, Any]
