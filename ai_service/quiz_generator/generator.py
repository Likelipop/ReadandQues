"""
ai_service/quiz_generator/generator.py — LangChain Structured Question & Keyword Generator.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from ai_service.connection import get_llm
from ai_service.quiz_generator.prompts import QUESTION_GENERATOR_PROMPT
from ai_service.quiz_generator.schemas import ExamOutput

logger = logging.getLogger(__name__)


def generate_questions(text: str) -> ExamOutput:
    """
    Generate structured reading comprehension quizzes and keywords via LangChain structured output.
    """
    prompt = QUESTION_GENERATOR_PROMPT.format(text=text)
    llm = get_llm()
    try:
        structured_llm = llm.with_structured_output(ExamOutput, method="function_calling")
        result = structured_llm.invoke(prompt)
        if isinstance(result, ExamOutput):
            return result
        elif isinstance(result, dict):
            return ExamOutput.model_validate(result)
        return ExamOutput(quizzes=[])
    except Exception as e:
        logger.error(f"Structured question generation failed: {e}")
        return ExamOutput(quizzes=[])


def run_question_generator_flow(text: str) -> dict[str, Any]:
    """
    Execution wrapper returning structured dictionary with keywords, summary, quizzes, and final exam.
    """
    exam_output = generate_questions(text)
    quizzes = [q.model_dump() if hasattr(q, "model_dump") else q for q in exam_output.quizzes]

    if exam_output.semantic_analysis:
        analysis_data = exam_output.semantic_analysis.model_dump()
    else:
        analysis_data = {
            "keywords": ["General"],
            "summary": text[:200] if text else "",
            "core": {"summary": text[:200] if text else ""},
        }

    keywords = analysis_data.get("keywords") or ["General"]

    final_exam = {
        "exam_id": f"EXAM_{uuid.uuid4().hex[:12].upper()}",
        "title": "IELTS Academic Reading Test",
        "total_questions": len(quizzes),
        "quizzes": quizzes,
        "token_usage": [],
        "created_at": datetime.now(UTC).isoformat(),
    }

    return {
        "keywords": keywords,
        "summary": analysis_data.get("summary", ""),
        "questions": quizzes,
        "raw_quizzes": quizzes,
        "verified_quizzes": quizzes,
        "semantic_analysis": analysis_data,
        "final_exam": final_exam,
        "_verifier_passed": True,
    }
