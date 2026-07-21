"""
ReadAndQues/AI_core/schemas.py — Canonical Pydantic schemas for AI pipeline & domain models.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ==========================================
# GENRE & THEME CLASSIFICATION
# ==========================================

class TextGenre(str, Enum):
    narrative   = "narrative"
    poetry      = "poetry"
    scientific  = "scientific"
    persuasive  = "persuasive"
    general     = "general"


class ThemeCategory(str, Enum):
    economy     = "Economy"
    society     = "Society"
    education   = "Education"
    technology  = "Technology"
    science     = "Science"
    environment = "Environment"
    culture     = "Culture"
    health      = "Health"
    general     = "General"


# ==========================================
# CORE & GENRE ANALYSIS
# ==========================================

class CoreAnalysis(BaseModel):
    summary: str = Field(..., description="2–3 sentence summary of the main content")
    central_theme: str = Field(default="", description="Central theme / message")
    secondary_themes: List[str] = Field(default_factory=list, description="Supporting themes")
    tone: str = Field(default="", description="e.g. formal, objective")
    tone_shifts: List[str] = Field(default_factory=list)
    structure_overview: str = Field(default="")
    key_terms: Dict[str, str] = Field(default_factory=dict)
    likely_misunderstood: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    emotional_arc: Optional[str] = Field(default=None)
    author_intent: Optional[str] = Field(default=None)
    irrelevant_snippets: List[str] = Field(default_factory=list)


class NarrativeAnalysis(BaseModel):
    characters: Dict[str, str] = Field(default_factory=dict)
    conflicts: List[str] = Field(default_factory=list)
    symbolism: List[str] = Field(default_factory=list)
    irony_or_foreshadowing: List[str] = Field(default_factory=list)
    narrative_perspective: str = Field(default="")
    unstated_implications: List[str] = Field(default_factory=list)


class PoetryAnalysis(BaseModel):
    imagery: List[str] = Field(default_factory=list)
    central_metaphor: Optional[str] = Field(default=None)
    sound_devices: List[str] = Field(default_factory=list)
    form_structure: str = Field(default="")
    multiple_interpretations: List[str] = Field(default_factory=list)


class ScientificAnalysis(BaseModel):
    research_question: str = Field(default="")
    hypothesis: Optional[str] = Field(default=None)
    methodology_summary: str = Field(default="")
    key_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    claims_vs_evidence: List[str] = Field(default_factory=list)
    terminology_glossary: Dict[str, str] = Field(default_factory=dict)


class PersuasiveAnalysis(BaseModel):
    central_claim: str = Field(default="")
    supporting_arguments: List[str] = Field(default_factory=list)
    unstated_assumptions: List[str] = Field(default_factory=list)
    rhetorical_strategies: List[str] = Field(default_factory=list)
    counterarguments_addressed: List[str] = Field(default_factory=list)
    counterarguments_ignored: List[str] = Field(default_factory=list)
    bias_indicators: List[str] = Field(default_factory=list)


class SemanticAnalysis(BaseModel):
    genre: TextGenre
    theme: ThemeCategory = Field(default=ThemeCategory.general)
    core: CoreAnalysis
    narrative:  Optional[NarrativeAnalysis]  = Field(default=None)
    poetry:     Optional[PoetryAnalysis]     = Field(default=None)
    scientific: Optional[ScientificAnalysis] = Field(default=None)
    persuasive: Optional[PersuasiveAnalysis] = Field(default=None)

    model_config = {"use_enum_values": True}


# ==========================================
# QUIZ & EXAM SCHEMAS
# ==========================================

class QuizItem(BaseModel):
    quiz_type: str = Field(..., description="'yes_no_notgiven', 'multiple_choice', or 'fill_in_blank'")
    question: str = Field(...)
    options: Optional[List[str]] = Field(default=None)
    correct_answer: str = Field(...)
    explanation: str = Field(...)
    supporting_text: str = Field(...)
    source_chunk_ids: Optional[Union[List[str], str]] = Field(default=None)


class ExamOutput(BaseModel):
    quizzes: List[QuizItem]


class VerifierFeedback(BaseModel):
    passed: bool = Field(...)
    rejected_indices: List[int] = Field(default_factory=list)
    reason: str = Field(default="")


class TokenUsageLog(BaseModel):
    node: str
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)


class GraphState(TypedDict):
    original_text: str
    exam_config: Dict[str, Any]
    semantic_analysis: Dict[str, Any]
    raw_quizzes: List[Dict[str, Any]]
    verified_quizzes: List[Dict[str, Any]]
    retry_count: int
    token_log: List[Dict[str, Any]]
    final_exam: Dict[str, Any]
