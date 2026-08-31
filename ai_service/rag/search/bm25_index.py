"""
ai_service/rag/search/bm25_index.py — Lexical Search & Text Processing with BM25.
"""

import logging
import os
import re
import spacy
from pymongo import MongoClient
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# Load standard English spaCy model
try:
    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except Exception as e:
    logger.warning(f"Could not load 'en_core_web_sm' spaCy model: {e}. Fallback to basic tokenizer.")
    _nlp = None

_bm25_index: BM25Okapi | None = None
_corpus_ids: list[str] = []


def clean_text(text: str) -> str:
    """Remove HTML entities and non-alphabetic characters, normalizing whitespace."""
    if not text:
        return ""
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def tokenize_and_lemmatize(text: str) -> list[str]:
    """Tokenize text into lowercase lemmatized words, removing stopwords and punctuation."""
    if not text:
        return []
    if _nlp is None:
        return [word.lower() for word in text.split() if word.isalnum()]

    doc = _nlp(text)
    return [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop and not token.is_punct and not token.is_space and token.is_alpha
    ]


def process_text_to_tokens(text: str) -> list[str]:
    """Full text preprocessing pipeline: cleans string and outputs normalized tokens."""
    cleaned = clean_text(text)
    return tokenize_and_lemmatize(cleaned)


def get_index() -> tuple[BM25Okapi | None, list[str]]:
    """Return the current BM25 index instance and corresponding article IDs list."""
    global _bm25_index, _corpus_ids
    if _bm25_index is None:
        rebuild_index()
    return _bm25_index, _corpus_ids


def rebuild_index() -> None:
    """Fetch all indexed article titles from MongoDB and build a fresh BM25Okapi index."""
    global _bm25_index, _corpus_ids

    logger.info("[BM25] Building index from gold_articles / article_index...")
    mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin")

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        db = client.get_database()
        
        # Try gold_articles first, then fallback to article_index
        col = db["gold_articles"] if "gold_articles" in db.list_collection_names() else db["article_index"]
        docs = list(col.find({"title": {"$ne": ""}}, {"article_id": 1, "title": 1, "_id": 1}))
    except Exception as e:
        logger.warning(f"[BM25] Could not load articles for index build: {e}")
        _bm25_index = None
        _corpus_ids = []
        return

    if not docs:
        logger.info("[BM25] No articles found to index.")
        _bm25_index = None
        _corpus_ids = []
        return

    _corpus_ids = [str(d.get("article_id") or d["_id"]) for d in docs]
    corpus_tokens = [process_text_to_tokens(d.get("title", "")) for d in docs]

    _bm25_index = BM25Okapi(corpus_tokens)
    logger.info(f"[BM25] Successfully built index for {len(docs)} documents.")


def search_bm25(query_tokens: list[str], n: int = 5, exclude_id: str | None = None) -> list[dict]:
    """Score documents in the BM25 index against query tokens and return top N matches."""
    bm25_index, corpus_ids = get_index()
    if bm25_index is None or not query_tokens:
        return []

    try:
        scores = bm25_index.get_scores(query_tokens)
        results = [
            {"id": corpus_ids[i], "score": float(scores[i])}
            for i in range(len(corpus_ids))
            if corpus_ids[i] != exclude_id and scores[i] > 0
        ]
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n]
    except Exception as e:
        logger.error(f"[BM25] Search error: {e}")
        return []
