"""
pipeline/ai_core/utils/config.py — AI Pipeline Configuration.
"""

from pydantic import BaseModel


class ExamConfig(BaseModel):
    word_count: int
    total_questions: int

    @classmethod
    def from_text(cls, text: str) -> "ExamConfig":
        wc = len(text.strip().split())
        if wc < 300:
            total = 3
        elif wc < 500:
            total = 5
        elif wc < 800:
            total = 7
        else:
            total = 10
        return cls(word_count=wc, total_questions=total)

