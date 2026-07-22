"""
database/BM25/text_preprocessing.py

Shared NLP text preprocessing logic (cleaning, tokenization, lemmatization).
Used by both the database (for building the BM25 index) and AI_core (for searching).
"""

import logging
import re

import spacy

logger = logging.getLogger(__name__)

# Load model một lần khi module được import
try:
    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except OSError:
    logger.error(
        "[TextPreprocessing] spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm"
    )
    _nlp = None


def clean_text(text: str) -> str:
    """Remove HTML entities, punctuation, numbers, extra spaces."""
    if not text:
        return ""
    text = re.sub(r"&[a-z]+;", " ", text)  # HTML entities
    text = re.sub(r"[^a-zA-Z\s]", " ", text)  # giữ lại chữ cái
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def tokenize_and_lemmatize(text: str) -> list[str]:
    """
    Dùng spaCy pipeline:
    - Lemmatize: "running" → "run", "studies" → "study"
    - Remove stopwords ("the", "is", "at"...)
    - Remove short tokens (len < 3)
    """
    if _nlp is None:
        # Fallback: simple split nếu spaCy không có
        return [t for t in text.split() if len(t) > 2]

    doc = _nlp(text)
    tokens = [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop
        and not token.is_punct
        and len(token.lemma_) > 2
        and token.is_alpha
    ]
    return tokens


def process_text_to_tokens(text: str) -> list[str]:
    """
    Full standard pipeline for converting raw text to BM25-ready tokens.
    """
    cleaned = clean_text(text)
    return tokenize_and_lemmatize(cleaned)
