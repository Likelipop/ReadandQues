"""
service/domain/enums.py — Domain Enums.
Clean ZEN re-exports from service.domain.models.
"""

from service.domain.models import Stage, Status, ThemeCategory

# Backward compatibility aliases
ArticleStage = Stage
MedallionStage = Stage
ArticleStatus = Status
AIStatus = Status

__all__ = [
    "Stage",
    "Status",
    "ThemeCategory",
    "ArticleStage",
    "MedallionStage",
    "ArticleStatus",
    "AIStatus",
]
