"""Configuration settings and calculations for shared domain operations."""

from dataclasses import dataclass


@dataclass
class ExamConfig:
    """Configuration for exam generation based on article word count."""

    word_count: int = 0
    total_questions: int = 0

    @classmethod
    def calculate_question_count(cls, word_count: int) -> int:
        """Calculate the recommended question count based on article word count.

        Rules:
        - Less than 300 words: 3 questions
        - 300 to 499 words: 5 questions
        - 500 to 799 words: 7 questions
        - 800+ words: 10 questions
        """
        if word_count < 300:
            return 3
        if word_count < 500:
            return 5
        if word_count < 800:
            return 7
        return 10

    @classmethod
    def from_text(cls, text: str) -> "ExamConfig":
        """Create an ExamConfig instance by calculating word count from text."""
        word_count = len(text.strip().split())
        total_questions = cls.calculate_question_count(word_count)
        return cls(word_count=word_count, total_questions=total_questions)

    @classmethod
    def from_word_count(cls, word_count: int) -> "ExamConfig":
        """Create an ExamConfig instance directly from word count."""
        total_questions = cls.calculate_question_count(word_count)
        return cls(word_count=word_count, total_questions=total_questions)


__all__ = ["ExamConfig"]
