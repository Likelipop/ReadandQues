"""
ai_service/rag/grounding/passage_proof.py — Passage Proof & Grounding Service.
"""

import logging
import os
from typing import Any

from pymongo import MongoClient

from ai_service.rag.search.vector_store import vector_search_chunks

logger = logging.getLogger(__name__)


def get_passage_proof(article_id: str, question_idx: int) -> dict[str, Any] | None:
    """Finds verbatim paragraph proof from ChromaDB for a specific quiz question."""
    mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin")
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        db = client.get_database()
        
        # Look in gold_articles first, then exams collection
        doc = db["gold_articles"].find_one({"article_id": article_id}) or db["exams"].find_one({"article_id": article_id})
    except Exception as e:
        logger.warning(f"Failed to fetch article exam from Mongo: {e}")
        doc = None

    if not doc:
        return None

    exams = doc.get("exams", [])
    quizzes = exams if isinstance(exams, list) and exams and "question" in exams[0] else (exams[0].get("quizzes", []) if exams and isinstance(exams[0], dict) else [])
    if not quizzes or question_idx < 0 or question_idx >= len(quizzes):
        return None

    q = quizzes[question_idx]
    q_text = q.get("question", "")
    correct = q.get("correct_answer", "")
    explanation = q.get("explanation", "")

    query_str = f"{q_text} {correct}"
    hits = vector_search_chunks(
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
