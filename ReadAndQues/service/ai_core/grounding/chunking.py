"""
service/ai_core/grounding/chunking.py — Semantic Chunking Engine.

Algorithm Flow:
1. Clean & normalize text preserving source offsets.
2. Split text into smallest sentence units.
3. Generate vector embeddings for each sentence unit.
4. Measure cosine similarity between neighboring sentences (s_i, s_{i+1}).
5. Detect semantic breakpoints where similarity drops significantly.
6. Form coherent semantic chunks from grouped sentences.
7. Enforce hard token size constraint (max 2000 tokens per chunk) using tiktoken.
"""

import hashlib
import logging
import re
from typing import Any

import numpy as np
import tiktoken
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MAX_CHUNK_TOKENS = 2000
DEFAULT_SIMILARITY_THRESHOLD = 0.50

# Lazy-loaded tokenizer and embedder
_tokenizer = None
_embedder = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        try:
            _tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _tokenizer = None
    return _tokenizer


def _count_tokens(text: str) -> int:
    enc = _get_tokenizer()
    if enc:
        return len(enc.encode(text))
    # Fallback approximation: 1 token ~ 0.75 words
    return int(len(text.split()) * 1.33)


def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from chromadb.utils import embedding_functions

            _embedder = embedding_functions.DefaultEmbeddingFunction()
        except Exception as e:
            logger.warning(f"DefaultEmbeddingFunction unavailable ({e}), using lexical vector fallback.")
            _embedder = None
    return _embedder


class SentenceUnit(BaseModel):
    text: str
    start_offset: int
    end_offset: int
    token_count: int = 0


class ArticleChunk(BaseModel):
    chunk_id: str
    text: str
    start_offset: int
    end_offset: int
    content_hash: str
    token_count: int = 0
    sentence_count: int = 0


def _split_into_sentences(text: str) -> list[SentenceUnit]:
    """Splits raw text into sentence units with precise start and end character offsets."""
    if not text or not text.strip():
        return []

    # Regex matching sentence boundaries (.!? followed by whitespace or line break)
    pattern = re.compile(r"([^.!?\n]+[.!?]+(?:\s+|\n+|$)|[^\n]+(?:\n+|$))")
    matches = pattern.finditer(text)

    sentences: list[SentenceUnit] = []
    for m in matches:
        raw_sentence = m.group(0)
        cleaned = raw_sentence.strip()
        if cleaned:
            start = m.start()
            end = m.end()
            t_count = _count_tokens(cleaned)
            sentences.append(
                SentenceUnit(
                    text=cleaned,
                    start_offset=start,
                    end_offset=end,
                    token_count=t_count,
                )
            )

    # Fallback to paragraph splitting if regex didn't extract multiple sentences
    if not sentences and text.strip():
        sentences.append(
            SentenceUnit(
                text=text.strip(),
                start_offset=0,
                end_offset=len(text),
                token_count=_count_tokens(text),
            )
        )

    return sentences


def _compute_embeddings(sentences: list[str]) -> np.ndarray:
    """Generates normalized vector embeddings for a list of sentence strings."""
    embedder = _get_embedder()
    if embedder:
        try:
            embs = embedder(sentences)
            embs_arr = np.array(embs, dtype=np.float32)
            # Normalize vectors
            norms = np.linalg.norm(embs_arr, axis=1, keepdims=True)
            norms[norms == 0] = 1e-10
            return embs_arr / norms
        except Exception as e:
            logger.warning(f"Embedding computation failed: {e}")

    # Fallback: simple character/word frequency vector
    vocabulary = sorted({w.lower() for s in sentences for w in re.findall(r"\w+", s)})
    if not vocabulary:
        return np.ones((len(sentences), 1), dtype=np.float32)

    vecs = []
    for s in sentences:
        words = re.findall(r"\w+", s.lower())
        vec = [words.count(w) for w in vocabulary]
        vec_arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(vec_arr)
        vecs.append(vec_arr / (norm if norm > 0 else 1.0))
    return np.array(vecs, dtype=np.float32)


def chunk_article_text(
    article_text: str,
    max_tokens: int = MAX_CHUNK_TOKENS,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[ArticleChunk]:
    """
    Executes Semantic Chunking over article text:
    1. Splits into sentences.
    2. Embeds sentences and measures consecutive cosine similarity.
    3. Finds semantic breakpoints.
    4. Merges into chunks and enforces max token constraint.
    """
    if not article_text or not article_text.strip():
        return []

    sentence_units = _split_into_sentences(article_text)
    if not sentence_units:
        return []

    if len(sentence_units) == 1:
        s = sentence_units[0]
        c_hash = hashlib.sha256(s.text.encode("utf-8")).hexdigest()[:16]
        return [
            ArticleChunk(
                chunk_id="chunk_0",
                text=s.text,
                start_offset=s.start_offset,
                end_offset=s.end_offset,
                content_hash=c_hash,
                token_count=s.token_count,
                sentence_count=1,
            )
        ]

    # Compute sentence embeddings
    sentence_texts = [s.text for s in sentence_units]
    embs = _compute_embeddings(sentence_texts)

    # Compute cosine similarity between adjacent sentences: s[i] and s[i+1]
    # Since vectors are normalized, dot product = cosine similarity
    similarities = np.sum(embs[:-1] * embs[1:], axis=1)

    # Determine dynamic breakpoint threshold (mean - 0.5 * std or similarity_threshold)
    if len(similarities) > 1:
        mean_sim = np.mean(similarities)
        std_sim = np.std(similarities)
        threshold = max(similarity_threshold, float(mean_sim - 0.5 * std_sim))
    else:
        threshold = similarity_threshold

    # Form initial semantic groups
    chunks: list[ArticleChunk] = []
    current_sentences: list[SentenceUnit] = [sentence_units[0]]
    current_token_count = sentence_units[0].token_count

    for i in range(len(similarities)):
        next_sentence = sentence_units[i + 1]
        sim = float(similarities[i])
        is_semantic_breakpoint = sim < threshold
        would_exceed_limit = (current_token_count + next_sentence.token_count) > max_tokens

        if (is_semantic_breakpoint and current_token_count >= 100) or would_exceed_limit:
            # Finalize current chunk
            chunk_text = " ".join([s.text for s in current_sentences])
            chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:16]
            chunks.append(
                ArticleChunk(
                    chunk_id=f"chunk_{len(chunks)}",
                    text=chunk_text,
                    start_offset=current_sentences[0].start_offset,
                    end_offset=current_sentences[-1].end_offset,
                    content_hash=chunk_hash,
                    token_count=current_token_count,
                    sentence_count=len(current_sentences),
                )
            )
            current_sentences = [next_sentence]
            current_token_count = next_sentence.token_count
        else:
            current_sentences.append(next_sentence)
            current_token_count += next_sentence.token_count

    # Final chunk flush
    if current_sentences:
        chunk_text = " ".join([s.text for s in current_sentences])
        chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:16]
        chunks.append(
            ArticleChunk(
                chunk_id=f"chunk_{len(chunks)}",
                text=chunk_text,
                start_offset=current_sentences[0].start_offset,
                end_offset=current_sentences[-1].end_offset,
                content_hash=chunk_hash,
                token_count=current_token_count,
                sentence_count=len(current_sentences),
            )
        )

    return chunks
