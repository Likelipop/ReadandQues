"""
NewsPipeline/resources/bm25_resource.py — BM25 index builder and MinIO pickle persistence.
"""

import io
import logging
import os
import pickle
import re
from datetime import UTC, datetime
from typing import Any

from dagster import ConfigurableResource
from dotenv import find_dotenv, load_dotenv
from minio import Minio
from rank_bm25 import BM25Okapi

from NewsPipeline.resources.minio_io_manager import get_minio_client

load_dotenv(find_dotenv(usecwd=True))

logger = logging.getLogger(__name__)

# Attempt to load spaCy English model for lemmatization
_nlp = None
try:
    import spacy

    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except Exception as e:
    logger.warning(f"BM25Resource: Could not load 'en_core_web_sm' spaCy model: {e}. Using fallback tokenizer.")


class BM25Resource(ConfigurableResource):
    """
    Resource that tokenizes article titles, builds a BM25Okapi lexical search index,
    serializes the index into a binary pickle payload, and uploads it to MinIO.
    """

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    bucket: str = "bm25-index"
    key: str = "gold_bm25_index/index.pkl"

    def _get_minio_client(self) -> Minio:
        return get_minio_client(
            endpoint=self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=self.minio_secure,
        )

    def clean_text(self, text: str) -> str:
        """Remove HTML entities and non-alphabetic characters, normalizing whitespace."""
        if not text:
            return ""
        text = re.sub(r"&[a-z]+;", " ", text)
        text = re.sub(r"[^a-zA-Z\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower()

    def tokenize_and_lemmatize(self, text: str) -> list[str]:
        """Tokenize text into lowercase lemmatized words, removing stopwords and punctuation."""
        if not text:
            return []
        if _nlp is None:
            return [w.lower() for w in text.split() if w.isalnum()]

        doc = _nlp(text)
        return [
            token.lemma_.lower()
            for token in doc
            if not token.is_stop and not token.is_punct and not token.is_space and token.is_alpha
        ]

    def process_text_to_tokens(self, text: str) -> list[str]:
        """Full text preprocessing: cleans string and outputs normalized tokens."""
        cleaned = self.clean_text(text)
        return self.tokenize_and_lemmatize(cleaned)

    def build_and_upload(self, docs: list[dict[str, Any]]) -> int:
        """
        Build BM25Okapi index from article records, serialize to pickle, and upload to MinIO.
        Each document dict must have 'article_id' (or '_id') and 'title'.
        """
        if not docs:
            logger.info("BM25Resource: No documents provided for index build.")
            return 0

        corpus_ids = [str(d.get("article_id") or d.get("_id")) for d in docs]
        corpus_tokens = [self.process_text_to_tokens(d.get("title", "")) for d in docs]

        bm25_index = BM25Okapi(corpus_tokens)

        payload = pickle.dumps(
            {
                "index": bm25_index,
                "corpus_ids": corpus_ids,
                "built_at": datetime.now(UTC).isoformat(),
                "doc_count": len(docs),
            }
        )

        client = self._get_minio_client()
        try:
            if not client.bucket_exists(self.bucket):
                client.make_bucket(self.bucket)
                logger.info(f"BM25Resource: Created MinIO bucket '{self.bucket}'.")
        except Exception as e:
            logger.debug(f"BM25Resource: Bucket check note for '{self.bucket}': {e}")

        client.put_object(
            bucket_name=self.bucket,
            object_name=self.key,
            data=io.BytesIO(payload),
            length=len(payload),
            content_type="application/octet-stream",
        )

        logger.info(f"BM25Resource: Uploaded index for {len(docs)} documents to '{self.bucket}/{self.key}'.")
        return len(docs)
