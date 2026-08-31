"""
NewsPipeline/assets/gold.py — Gold Assets: Content cleaning, semantic chunking, and BM25 indexing.
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any

import trafilatura
from bs4 import BeautifulSoup
from dagster import Output, asset

from NewsPipeline.partitions import daily_partitions
from NewsPipeline.resources.bm25_resource import BM25Resource
from NewsPipeline.resources.chroma_resource import ChromaResource
from NewsPipeline.resources.minio_io_manager import MinIOResource
from NewsPipeline.resources.mongo_io_manager import get_mongo_client

logger = logging.getLogger(__name__)


def _extract_title_from_html(html_str: str, default_title: str = "Untitled") -> str:
    """Extract clean title from raw HTML with BeautifulSoup fallback."""
    if not html_str:
        return default_title
    try:
        soup = BeautifulSoup(html_str, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        h1 = soup.find("h1")
        if h1 and h1.text:
            return h1.text.strip()
    except Exception:
        pass
    return default_title or "Untitled"


@asset(
    group_name="gold",
    partitions_def=daily_partitions,
    io_manager_key="mongo_io_manager",
    description="Parse raw HTML into clean structured articles and save to MongoDB 'gold_content'.",
)
def gold_content(
    context,
    silver_raw_html: list[dict[str, Any]],
    minio_resource: MinIOResource,
) -> Output[list[dict[str, Any]]]:
    """
    Partitioned per day.
    Reads each article's raw HTML from MinIO, extracts clean text and title,
    and returns documents to be persisted into MongoDB collection 'gold_content'.
    """
    target_date = context.partition_key
    gold_docs: list[dict[str, Any]] = []

    for item in silver_raw_html:
        article_id = item["article_id"]
        try:
            raw_html = minio_resource.read_html(target_date, article_id)
            raw_text = trafilatura.extract(raw_html, include_comments=False) or ""
            title = _extract_title_from_html(raw_html, default_title=item.get("title", "Untitled"))
            word_count = len(raw_text.split())

            doc = {
                "article_id": article_id,
                "url": item.get("url", ""),
                "title": title,
                "source": item.get("source", ""),
                "original_text": raw_text,
                "word_count": word_count,
                "published_at": item.get("published_at", ""),
                "partition_date": target_date,
                "created_at": datetime.now(UTC).isoformat(),
            }
            gold_docs.append(doc)
        except Exception as e:
            context.log.warning(f"Gold: Error parsing content for {article_id}: {e}")

    context.log.info(f"Gold: Processed {len(gold_docs)} articles for date {target_date}.")

    return Output(
        value=gold_docs,
        metadata={
            "articles_count": len(gold_docs),
            "partition_date": target_date,
        },
    )


@asset(
    group_name="gold",
    partitions_def=daily_partitions,
    description="Split daily article text into semantic chunks and upsert into ChromaDB 'gold_semantic_chunks'.",
)
def gold_semantic_chunks(
    context,
    gold_content: list[dict[str, Any]],
    chroma_resource: ChromaResource,
) -> Output[dict[str, Any]]:
    """
    Partitioned per day.
    Performs semantic chunking on all articles in the daily partition
    and performs a batch upsert into ChromaDB collection 'gold_semantic_chunks'.
    """
    target_date = context.partition_key
    all_chunks: list[dict[str, Any]] = []

    # Initialize semantic chunker with lightweight fallback
    chunker = None
    try:
        from langchain_experimental.text_splitter import SemanticChunker
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        chunker = SemanticChunker(embeddings)
    except Exception as e:
        context.log.info(f"Gold: Using paragraph-based chunker fallback ({e})")

    for doc in gold_content:
        article_id = doc["article_id"]
        text = doc.get("original_text", "")
        title = doc.get("title", "")

        if not text.strip():
            continue

        if chunker:
            try:
                raw_chunks = chunker.split_text(text)
            except Exception:
                raw_chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
        else:
            raw_chunks = [p.strip() for p in text.split("\n\n") if p.strip()]

        for i, chunk_text in enumerate(raw_chunks):
            if not chunk_text.strip():
                continue
            all_chunks.append(
                {
                    "id": f"{article_id}_{i}",
                    "document": chunk_text,
                    "metadata": {
                        "article_id": str(article_id),
                        "title": str(title),
                        "partition_date": str(target_date),
                        "chunk_index": i,
                    },
                }
            )

    indexed_count = chroma_resource.upsert_chunks("gold_semantic_chunks", all_chunks)
    context.log.info(f"Gold: Indexed {indexed_count} chunks into ChromaDB for {target_date}.")

    return Output(
        value={"partition_date": target_date, "total_chunks": indexed_count},
        metadata={"total_chunks": indexed_count, "partition_date": target_date},
    )


@asset(
    group_name="gold",
    deps=["gold_content"],
    description="Scan all documents in MongoDB 'gold_content', build BM25 index, and upload pickle to MinIO.",
)
def gold_bm25_index(context, bm25_resource: BM25Resource) -> Output[dict[str, Any]]:
    """
    Corpus-level unpartitioned asset.
    Scans all gold_content documents across the entire corpus, generates BM25 Okapi index,
    and uploads pickled binary artifact to MinIO bucket 'bm25-index'.
    """
    try:
        client = get_mongo_client()
        db_name = os.getenv("MONGO_DB_NAME") or os.getenv("MONGO_INITDB_DATABASE", "articlesDB")
        db = client[db_name]
        docs = list(db["gold_content"].find({"title": {"$ne": ""}}, {"article_id": 1, "title": 1, "_id": 0}))
    except Exception as e:
        context.log.error(f"Gold BM25: Error querying MongoDB: {e}")
        docs = []

    if not docs:
        context.log.info("Gold BM25: No documents found in 'gold_content'.")
        return Output(value={"status": "empty", "doc_count": 0}, metadata={"doc_count": 0})

    count = bm25_resource.build_and_upload(docs)
    context.log.info(f"Gold BM25: Successfully built and uploaded index for {count} documents.")

    return Output(
        value={"status": "success", "doc_count": count},
        metadata={"doc_count": count},
    )
