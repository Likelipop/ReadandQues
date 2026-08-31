"""Domain enums shared across Backend, AI Service, and Data Pipeline."""

from enum import Enum


class Stage(str, Enum):
    """Medallion storage layer stages."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class Status(str, Enum):
    """Pipeline processing statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentIntent(str, Enum):
    """Agent intent classifications."""
    NEWS = "news"
    TEACHER = "teacher"
    QUIZ_HELPER = "quiz_helper"
    UNKNOWN = "unknown"


class ThemeCategory(str, Enum):
    """Broad article theme categories."""
    ECONOMY = "Economy"
    SOCIETY = "Society"
    EDUCATION = "Education"
    TECHNOLOGY = "Technology"
    SCIENCE = "Science"
    ENVIRONMENT = "Environment"
    CULTURE = "Culture"
    HEALTH = "Health"
    GENERAL = "General"


__all__ = [
    "AgentIntent",
    "Stage",
    "Status",
    "ThemeCategory",
]
