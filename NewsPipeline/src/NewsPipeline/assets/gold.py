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


@asset(
    group_name="gold",
    partitions_def=daily_partitions,
    io_manager_key="mongo_io_manager",
    description="Persist clean sanitized articles to MongoDB 'gold_content' and archive to MinIO 'gold-content'.",
)
def gold_content(
    context,
    silver_cleaned_articles: list[dict[str, Any]],
    minio_resource: MinIOResource,
) -> Output[list[dict[str, Any]]]:
    """
    Partitioned per day.
    Takes sanitized clean articles from the Silver layer,
    archives gold copies to MinIO 'gold-content/<date>/<article_id>.json',
    and returns documents to be persisted into MongoDB collection 'gold_content'.
    """
    target_date = context.partition_key
    gold_docs: list[dict[str, Any]] = []

    for item in silver_cleaned_articles:
        article_id = item["article_id"]
        try:
            doc = {
                "article_id": article_id,
                "url": item.get("url", ""),
                "title": item.get("title", "Untitled"),
                "source": item.get("source", ""),
                "image_url": item.get("image_url", ""),
                "thumbnail_url": item.get("thumbnail_url", ""),
                "original_text": item.get("original_text", ""),
                "word_count": item.get("word_count", 0),
                "published_at": item.get("published_at", ""),
                "partition_date": target_date,
                "created_at": datetime.now(UTC).isoformat(),
            }
            # Archive gold document to MinIO 'gold-content' bucket
            minio_resource.save_gold_article(target_date, article_id, doc)
            gold_docs.append(doc)
        except Exception as e:
            context.log.warning(f"Gold: Error archiving article {article_id}: {e}")

    context.log.info(f"Gold: Processed and archived {len(gold_docs)} clean articles for date {target_date}.")

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
    and performs micro-batched upserts into ChromaDB collection 'gold_semantic_chunks'.
    """
    target_date = context.partition_key
    total_indexed = 0

    # Use lightweight and reliable text splitter to avoid PyTorch OOM crashes in Docker
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    except Exception as e:
        context.log.info(f"Gold: Using simple paragraph chunker fallback ({e})")
        text_splitter = None

    current_batch: list[dict[str, Any]] = []

    for doc in gold_content:
        article_id = doc.get("article_id", "")
        text = doc.get("original_text", "")
        title = doc.get("title", "")

        if not text.strip() or not article_id:
            continue

        if text_splitter:
            try:
                raw_chunks = text_splitter.split_text(text)
            except Exception:
                raw_chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
        else:
            raw_chunks = [p.strip() for p in text.split("\n\n") if p.strip()]

        for i, chunk_text in enumerate(raw_chunks):
            if not chunk_text.strip():
                continue
            current_batch.append(
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

        # Flush in micro-batches of 5 chunks
        if len(current_batch) >= 5:
            total_indexed += chroma_resource.upsert_chunks("gold_semantic_chunks", current_batch)
            current_batch = []

    if current_batch:
        total_indexed += chroma_resource.upsert_chunks("gold_semantic_chunks", current_batch)

    context.log.info(f"Gold: Indexed {total_indexed} chunks into ChromaDB for {target_date}.")

    return Output(
        value={"partition_date": target_date, "total_chunks": total_indexed},
        metadata={"total_chunks": total_indexed, "partition_date": target_date},
    )


@asset(
    group_name="gold",
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


def extract_keywords_from_bm25(
    title: str,
    text: str,
    bm25_index: Any,
    bm25_resource: BM25Resource,
    max_keywords: int = 2,
    min_score_ratio: float = 0.5,
) -> list[str]:
    """
    Extract 1 to 2 top keywords for an article using BM25 token frequencies and IDF weights.
    Returns 1 keyword if the second keyword score is below min_score_ratio * top_score.
    """
    # 1. Sample title (weighted x2) and first 1500 chars of text
    content_sample = f"{title} {title} {text[:1500]}".strip()
    if not content_sample:
        return ["General"]

    # 2. Tokenize and lemmatize
    tokens = [t for t in bm25_resource.process_text_to_tokens(content_sample) if len(t) > 2 and t.isalpha()]
    if not tokens:
        return ["General"]

    # 3. Term Frequency (TF)
    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1

    # 4. Score = TF * IDF
    idf_dict = getattr(bm25_index, "idf", {}) if bm25_index else {}
    scored: list[tuple[str, float]] = []
    for token, count in tf.items():
        idf = idf_dict.get(token, 1.0)
        score = count * idf
        scored.append((token, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    if not scored:
        return ["General"]

    # 5. Select top 1 or 2 keywords
    top_word, top_score = scored[0]
    keywords = [top_word.capitalize()]

    if max_keywords >= 2 and len(scored) > 1:
        second_word, second_score = scored[1]
        if second_score >= (top_score * min_score_ratio):
            keywords.append(second_word.capitalize())

    return keywords


@asset(
    group_name="gold",
    deps=[gold_bm25_index],
    description="Incremental upsert: Extract top 1-2 BM25 keywords for all articles in MongoDB missing keywords.",
)
def gold_article_keywords(context, bm25_resource: BM25Resource) -> Output[dict[str, Any]]:
    """
    Incremental asset.
    Scans MongoDB 'gold_content' for documents without keywords, extracts top 1-2 keywords
    using the BM25 index and IDF weights, and performs an in-place $set update.
    """
    try:
        client = get_mongo_client()
        db_name = os.getenv("MONGO_DB_NAME") or os.getenv("MONGO_INITDB_DATABASE", "articlesDB")
        db = client[db_name]
        collection = db["gold_content"]

        # Incremental filter: only documents missing keywords or with empty keywords list
        query = {
            "$or": [
                {"keywords": {"$exists": False}},
                {"keywords": None},
                {"keywords": []},
            ]
        }
        unlabeled_docs = list(
            collection.find(query, {"_id": 1, "article_id": 1, "title": 1, "original_text": 1})
        )
    except Exception as e:
        context.log.error(f"Gold Keywords: Error querying MongoDB: {e}")
        unlabeled_docs = []

    if not unlabeled_docs:
        context.log.info("Gold Keywords: All articles in MongoDB already have keywords. Nothing to update.")
        return Output(
            value={"status": "skipped", "updated_count": 0},
            metadata={"updated_count": 0},
        )

    # Load BM25 index from MinIO
    bm25_index = bm25_resource.load_index()

    updated_count = 0
    for doc in unlabeled_docs:
        title = doc.get("title", "")
        text = doc.get("original_text", "")
        keywords = extract_keywords_from_bm25(title, text, bm25_index, bm25_resource)

        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"keywords": keywords, "theme": keywords[0]}},
        )
        updated_count += 1

    context.log.info(f"Gold Keywords: Successfully upserted keywords for {updated_count} articles.")

    return Output(
        value={"status": "success", "updated_count": updated_count},
        metadata={"updated_count": updated_count},
    )
