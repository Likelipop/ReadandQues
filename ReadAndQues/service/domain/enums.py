"""
service/domain/enums.py — Single Source of Truth for Domain Enums.
"""

from enum import Enum


class Stage(str, Enum):
    """Medallion storage layer stage."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class Status(str, Enum):
    """Pipeline processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    # Aliases
    CRAWLING = "pending"
    IN_PROGRESS = "processing"
    PENDING_GENERATION = "pending"


class ThemeCategory(str, Enum):
    GENERAL = "General"
    ECONOMY = "Economy"
    SOCIETY = "Society"
    EDUCATION = "Education"
    TECHNOLOGY = "Technology"
    SCIENCE = "Science"
    ENVIRONMENT = "Environment"
    CULTURE = "Culture"
    HEALTH = "Health"


class Genre(str, Enum):
    GENERAL = "general"
    SCIENTIFIC = "scientific"
    NARRATIVE = "narrative"
    PERSUASIVE = "persuasive"
    POETRY = "poetry"


class AgentIntent(str, Enum):
    NEWS = "news"
    TEACHER = "teacher"
    QUIZ_HELPER = "quiz_helper"
    UNKNOWN = "unknown"


# Aliases
ArticleStage = Stage
MedallionStage = Stage
ArticleStatus = Status
AIStatus = Status

__all__ = [
    "Stage",
    "Status",
    "ThemeCategory",
    "Genre",
    "AgentIntent",
    "ArticleStage",
    "MedallionStage",
    "ArticleStatus",
    "AIStatus",
]
