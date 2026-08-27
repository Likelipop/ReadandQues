"""
service/domain/contracts.py — Backward-compatibility alias layer.
Prefer importing directly from `service.domain.models`.
"""

from service.domain.models import (
    Article,
    Exam,
    ExamAttempt,
    Option,
    Question,
    RawSourceManifest,
    Stage,
    Status,
    ThemeCategory,
    generate_article_id,
    minio_bronze_prefix,
    minio_gold_prefix,
    minio_silver_prefix,
)

# Backward-compatibility class aliases
ArticleContract = Article
ArticleIndexContract = Article
ExamDocContract = Article
ExamContract = Exam
QuizItemContract = Question
QuizOptionContract = Option
ExamAttemptContract = ExamAttempt
RawSourceManifestContract = RawSourceManifest

__all__ = [
    "Article",
    "Exam",
    "Question",
    "Option",
    "ExamAttempt",
    "RawSourceManifest",
    "Stage",
    "Status",
    "ThemeCategory",
    "generate_article_id",
    "minio_bronze_prefix",
    "minio_silver_prefix",
    "minio_gold_prefix",
    # Aliases
    "ArticleContract",
    "ArticleIndexContract",
    "ExamDocContract",
    "ExamContract",
    "QuizItemContract",
    "QuizOptionContract",
    "ExamAttemptContract",
    "RawSourceManifestContract",
]
