"""
articles/services package — Public Web Service Interface.
"""

from .exam_generation import trigger_async_exam_generation
from .marker_search import get_related_articles_from_markers
from .pipeline_orchestrator import import_and_trigger_pipeline
from .user_stars import deduct_user_star, refund_user_star

__all__ = [
    "import_and_trigger_pipeline",
    "trigger_async_exam_generation",
    "deduct_user_star",
    "refund_user_star",
    "get_related_articles_from_markers",
]
