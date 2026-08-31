"""
service/infrastructure/bm25/text_processing.py — Natural Language Processing & Text Preprocessing.
Provides clean tokenization and lemmatization powered by spaCy.
"""

import logging
import re
import spacy

logger = logging.getLogger(__name__)

# Load standard English spaCy model (disable parser and NER for fast tokenization)
try:
    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except Exception as e:
    logger.warning(f"Could not load 'en_core_web_sm' spaCy model: {e}. Fallback to basic tokenizer.")
    _nlp = None


def clean_text(text: str) -> str:
    """
    Remove HTML entities and non-alphabetic characters, normalizing extra whitespaces.
    """
    if not text:
        return ""
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def tokenize_and_lemmatize(text: str) -> list[str]:
    """
    Tokenize text into lowercase lemmatized words, removing stopwords and punctuation.
    """
    if not text:
        return []

    if _nlp is None:
        # Basic split fallback if spaCy is not available
        return [word.lower() for word in text.split() if word.isalnum()]

    doc = _nlp(text)
    return [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop and not token.is_punct and not token.is_space and token.is_alpha
    ]


def process_text_to_tokens(text: str) -> list[str]:
    """
    Full text preprocessing pipeline: cleans string and outputs normalized tokens.
    """
    cleaned = clean_text(text)
    return tokenize_and_lemmatize(cleaned)
