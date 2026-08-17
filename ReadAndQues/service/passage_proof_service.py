"""
service/passage_proof_service.py — Passage Proof & Grounding Service.

Grounds quiz questions & correct answers to the exact paragraph chunk in ChromaDB.
"""

import logging
from typing import Any, Dict, Optional
import service.infrastructure.chroma.vector_store as vector_store
import service.infrastructure.mongo.exam_store as exam_store

logger = logging.getLogger(__name__)


def get_passage_proof(article_id: str, question_idx: int) -> Optional[Dict[str, Any]]:
    """
    Finds verbatim paragraph proof from ChromaDB for a specific quiz question.
    """
    exam_doc = exam_store.get_exam(article_id)
    if not exam_doc:
        return None

    exams = exam_doc.get("exams", [])
    if not exams or not exams[0].get("quizzes"):
        return None

    quizzes = exams[0]["quizzes"]
    if question_idx < 0 or question_idx >= len(quizzes):
        return None

    q = quizzes[question_idx]
    q_text = q.get("question", "")
    correct = q.get("correct_answer", "")
    explanation = q.get("explanation", "")

    query_str = f"{q_text} {correct}"
    hits = vector_store.vector_search_chunks(
        query=query_str,
        limit=1,
        where_filter={"article_id": str(article_id)},
    )

    if not hits:
        return {
            "question_index": question_idx,
            "question_text": q_text,
            "correct_answer": correct,
            "explanation": explanation,
            "proof_found": False,
            "proof_excerpt": "",
            "paragraph_id": None,
        }

    best_hit = hits[0]
    return {
        "question_index": question_idx,
        "question_text": q_text,
        "correct_answer": correct,
        "explanation": explanation,
        "proof_found": True,
        "proof_excerpt": best_hit.get("text", ""),
        "paragraph_id": best_hit.get("id"),
        "confidence_score": best_hit.get("score", 1.0),
    }
