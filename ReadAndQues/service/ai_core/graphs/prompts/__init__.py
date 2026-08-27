"""
service/ai_core/graphs/prompts — Centralized prompts for AI Core modules.
"""

from .explained import DYNAMIC_EXPLAINED_PROMPT
from .question_generator import QUESTION_GENERATOR_PROMPT

__all__ = [
    "DYNAMIC_EXPLAINED_PROMPT",
    "QUESTION_GENERATOR_PROMPT",
]
