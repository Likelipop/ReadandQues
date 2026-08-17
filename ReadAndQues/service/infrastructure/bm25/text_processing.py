"""
service/infrastructure/bm25/text_processing.py — Shared NLP text preprocessing (cleaning, tokenization, lemmatization).
"""

import logging
import re
import spacy

logger = logging.getLogger(__name__)

# Load model once when module is imported
try:
    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except OSError:
    try:
        logger.info("[TextPreprocessing] Model 'en_core_web_sm' not found, downloading...")
        from spacy.cli import download
        download("en_core_web_sm")
        _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    except Exception as e:
        logger.error(
            f"[TextPreprocessing] spaCy model 'en_core_web_sm' failed to download/load: {e}"
        )
        _nlp = None


def clean_text(text: str) -> str:
    """Remove HTML entities, punctuation, numbers, extra spaces."""
    if not text:
        return ""
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def tokenize_and_lemmatize(text: str) -> list[str]:
    if _nlp is None:
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
    cleaned = clean_text(text)
    return tokenize_and_lemmatize(cleaned)
