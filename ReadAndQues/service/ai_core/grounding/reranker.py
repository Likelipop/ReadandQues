"""
service/ai_core/grounding/reranker.py — Cross-Encoder Reranking Module.

Reranks candidate chunks (typically Top 20 from Hybrid RRF Search) down to Top 5 high-precision chunks.
"""

import logging
import re
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_cross_encoder_model = None


def _get_cross_encoder():
    global _cross_encoder_model
    if _cross_encoder_model is None:
        try:
            from sentence_transformers import CrossEncoder

            _cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("Loaded CrossEncoder model: ms-marco-MiniLM-L-6-v2")
        except Exception:
            _cross_encoder_model = "fallback"
    return _cross_encoder_model


def _compute_lexical_dense_interaction(query: str, text: str) -> float:
    """Computes a precise query-passage interaction score for reranking."""
    if not query.strip() or not text.strip():
        return 0.0

    q_tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    if not q_tokens:
        return 0.5

    text_lower = text.lower()
    total_tokens = max(len(text_lower.split()), 1)

    # Term coverage
    covered_terms = sum(1 for t in q_tokens if t in text_lower)
    coverage_ratio = covered_terms / len(q_tokens)

    # Exact query phrase boost
    phrase_boost = 1.0 if query.lower() in text_lower else 0.0

    # Term frequency density
    tf_sum = sum(text_lower.count(t) for t in q_tokens)
    tf_density = min(tf_sum / total_tokens, 1.0)

    # Combined cross score
    score = (0.5 * coverage_ratio) + (0.3 * tf_density) + (0.2 * phrase_boost)
    return round(float(score), 4)


def rerank_chunks(
    query: str,
    candidates: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Reranks a list of candidate documents/chunks based on Cross-Encoder semantic relevance.
    Input: candidates (e.g. Top 20 from Hybrid Search)
    Output: Top 5 reranked candidates sorted by rerank_score descending.
    """
    if not candidates or not query.strip():
        return candidates[:top_k]

    model = _get_cross_encoder()

    scored_candidates = []
    if model != "fallback" and model is not None:
        try:
            pairs = [(query, c.get("text", "")) for c in candidates]
            scores = model.predict(pairs)
            for hit, score in zip(candidates, scores, strict=False):
                c_copy = dict(hit)
                c_copy["rerank_score"] = round(float(score), 4)
                scored_candidates.append(c_copy)
        except Exception as e:
            logger.warning(f"CrossEncoder prediction failed ({e}), falling back to interaction scoring.")
            scored_candidates = []

    if not scored_candidates:
        # High-precision interaction reranker
        for hit in candidates:
            c_copy = dict(hit)
            text = c_copy.get("text", "")
            rrf_base = c_copy.get("rrf_score", 0.0)
            interaction_score = _compute_lexical_dense_interaction(query, text)

            # Combined weighted score
            final_rerank_score = (0.7 * interaction_score) + (0.3 * min(rrf_base * 10, 1.0))
            c_copy["rerank_score"] = round(final_rerank_score, 4)
            scored_candidates.append(c_copy)

    # Sort descending by rerank_score
    scored_candidates.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)

    return scored_candidates[:top_k]
