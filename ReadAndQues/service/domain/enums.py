from enum import Enum


class ArticleStatus(str, Enum):
    CRAWLING = "crawling"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AIStatus(str, Enum):
    PENDING_GENERATION = "pending_generation"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ArticleStage(str, Enum):
    """Tracks which Medallion layer an article has been written to in MinIO."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


# Backward-compat alias — will be removed after full migration
MedallionStage = ArticleStage


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
