"""
ai_core/schemas.py — Canonical Pydantic schema layer (SSOT).

ALL domain models live here. Both ai_core (LangGraph nodes) and articles
(Django views / MongoDB serialization) import FROM this module.
This breaks the circular-import risk that existed when schemas lived in articles/models.py.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ==========================================
# GENRE CLASSIFICATION
# ==========================================

class TextGenre(str, Enum):
    narrative   = "narrative"    # fiction, novel, short story, play
    poetry      = "poetry"       # poem, lyric
    scientific  = "scientific"   # research paper, academic article
    persuasive  = "persuasive"   # editorial, opinion, news analysis
    general     = "general"      # everything else (default)


class ThemeCategory(str, Enum):
    economy     = "Economy"      # Kinh tế, thương mại, tài chính
    society     = "Society"      # Xã hội, con người, đời sống
    education   = "Education"    # Giáo dục, học tập, trường học
    technology  = "Technology"   # Công nghệ, kỹ thuật, trí tuệ nhân tạo
    science     = "Science"      # Khoa học, tự nhiên, vũ trụ, sinh học
    environment = "Environment"  # Môi trường, biến đổi khí hậu, sinh thái
    culture     = "Culture"      # Văn hóa, nghệ thuật, lịch sử, âm nhạc
    health      = "Health"       # Sức khỏe, y tế, y học
    general     = "General"      # Tổng hợp / Khác


# ==========================================
# CORE LAYER — applies to ALL text types
# ==========================================

class CoreAnalysis(BaseModel):
    summary: str = Field(..., description="2–3 sentence summary of the main content")
    central_theme: str = Field(default="", description="Central theme / message")
    secondary_themes: List[str] = Field(default_factory=list, description="Supporting themes, if any")
    tone: str = Field(default="", description="e.g. formal, satirical, melancholic, objective…")
    tone_shifts: List[str] = Field(
        default_factory=list,
        description="Points where tone changes, e.g. 'shifts from optimistic to desperate in paragraph 3'"
    )
    structure_overview: str = Field(
        default="",
        description="How the text is organised: chronological, argumentative, contrastive…"
    )
    key_terms: Dict[str, str] = Field(
        default_factory=dict,
        description="Important terms/concepts → concise definitions for the reader"
    )
    likely_misunderstood: List[str] = Field(
        default_factory=list,
        description="What first-time readers easily miss or misread"
    )
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Passages open to multiple interpretations — useful for 'evaluate' questions"
    )
    emotional_arc: Optional[str] = Field(
        default=None,
        description="Emotional progression across the text, if present"
    )
    author_intent: Optional[str] = Field(
        default=None,
        description="What the author aimed to achieve by writing this text"
    )


# ==========================================
# NARRATIVE / LITERARY — fiction, novel, drama
# ==========================================

class NarrativeAnalysis(BaseModel):
    characters: Dict[str, str] = Field(
        default_factory=dict,
        description="Character name → primary motivation / inner conflict"
    )
    conflicts: List[str] = Field(
        default_factory=list,
        description="Main conflicts: internal, interpersonal, societal…"
    )
    symbolism: List[str] = Field(
        default_factory=list,
        description="Symbols and their meanings"
    )
    irony_or_foreshadowing: List[str] = Field(default_factory=list)
    narrative_perspective: str = Field(
        default="",
        description="Point of view, narrator reliability"
    )
    unstated_implications: List[str] = Field(
        default_factory=list,
        description="Things implied but never stated outright"
    )


# ==========================================
# POETRY
# ==========================================

class PoetryAnalysis(BaseModel):
    imagery: List[str] = Field(default_factory=list)
    central_metaphor: Optional[str] = Field(default=None)
    sound_devices: List[str] = Field(
        default_factory=list,
        description="Rhyme, rhythm, alliteration…"
    )
    form_structure: str = Field(
        default="",
        description="Poetic form, stanza count, rhyme scheme"
    )
    multiple_interpretations: List[str] = Field(
        default_factory=list,
        description="Different valid readings of the poem"
    )


# ==========================================
# SCIENTIFIC / ACADEMIC PAPER
# ==========================================

class ScientificAnalysis(BaseModel):
    research_question: str = Field(default="")
    hypothesis: Optional[str] = Field(default=None)
    methodology_summary: str = Field(default="")
    key_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    claims_vs_evidence: List[str] = Field(
        default_factory=list,
        description="Where conclusions appear broader than the actual evidence"
    )
    terminology_glossary: Dict[str, str] = Field(default_factory=dict)


# ==========================================
# OPINION / PERSUASIVE / NEWS
# ==========================================

class PersuasiveAnalysis(BaseModel):
    central_claim: str = Field(default="")
    supporting_arguments: List[str] = Field(default_factory=list)
    unstated_assumptions: List[str] = Field(default_factory=list)
    rhetorical_strategies: List[str] = Field(
        default_factory=list,
        description="e.g. emotional appeal, statistical evidence…"
    )
    counterarguments_addressed: List[str] = Field(default_factory=list)
    counterarguments_ignored: List[str] = Field(
        default_factory=list,
        description="Valid counter-arguments the author does not acknowledge"
    )
    bias_indicators: List[str] = Field(
        default_factory=list,
        description="Signs of bias in the presentation"
    )


# ==========================================
# SEMANTIC ANALYSIS — top-level document
# ==========================================

class SemanticAnalysis(BaseModel):
    genre: TextGenre
    theme: ThemeCategory = Field(default=ThemeCategory.general, description="Primary theme/topic of the reading passage")
    core: CoreAnalysis
    narrative:  Optional[NarrativeAnalysis]  = Field(default=None)
    poetry:     Optional[PoetryAnalysis]     = Field(default=None)
    scientific: Optional[ScientificAnalysis] = Field(default=None)
    persuasive: Optional[PersuasiveAnalysis] = Field(default=None)

    model_config = {"use_enum_values": True}


# ==========================================
# QUIZ / EXAM SCHEMAS
# ==========================================

class QuizItem(BaseModel):
    quiz_type: str = Field(
        ...,
        description="'yes_no_notgiven', 'multiple_choice', or 'fill_in_blank'"
    )
    question: str = Field(...)
    options: Optional[List[str]] = Field(
        default=None,
        description="Required for yes_no_notgiven and multiple_choice; null for fill_in_blank"
    )
    correct_answer: str = Field(...)
    explanation: str = Field(...)
    supporting_text: str = Field(
        ...,
        description="Verbatim sentence(s) from the article that ground the answer"
    )
    source_chunk_ids: Optional[Union[List[str], str]] = Field(
        default=None,
        description="Optional reference to chunk IDs; null when chunking is not used"
    )


class ExamOutput(BaseModel):
    """Structured output schema for the question_planner node."""
    quizzes: List[QuizItem]


# ==========================================
# VERIFIER FEEDBACK SCHEMA
# ==========================================

class VerifierFeedback(BaseModel):
    """Structured output schema for the verifier node."""
    passed: bool = Field(
        ...,
        description="True if all questions are grounded in the article text"
    )
    rejected_indices: List[int] = Field(
        default_factory=list,
        description="0-based indices of questions that failed verification"
    )
    reason: str = Field(
        default="",
        description="Brief explanation of why questions were rejected, if any"
    )


# ==========================================
# TOKEN USAGE LOG (embedded in Exam)
# ==========================================

class TokenUsageLog(BaseModel):
    node: str           # "analyzer", "question_planner", "verifier"
    input_tokens: int   = Field(default=0)
    output_tokens: int  = Field(default=0)


# ==========================================
# LANGGRAPH STATE
# ==========================================

class GraphState(TypedDict):
    """
    Shared state passed between all 4 LangGraph nodes.

    Flow:
      analyzer → question_planner → verifier ──(pass)──→ formatter → END
                       ↑____________________(retry, max 2)__|
    """
    original_text:      str
    exam_config:        Dict[str, Any]          # ExamConfig.model_dump()
    semantic_analysis:  Dict[str, Any]          # SemanticAnalysis.model_dump() — from Node 1
    raw_quizzes:        List[Dict[str, Any]]    # QuizItem list — from Node 2
    verified_quizzes:   List[Dict[str, Any]]    # QuizItem list (cleaned) — from Node 3
    retry_count:        int                     # guard: prevent infinite retry loop
    token_log:          List[Dict[str, Any]]    # TokenUsageLog list — accumulated
    final_exam:         Dict[str, Any]          # formatted Exam — from Node 4
