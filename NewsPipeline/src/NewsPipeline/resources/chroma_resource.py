"""
NewsPipeline/resources/chroma_resource.py — ChromaDB vector database management resource.
"""

import logging
import os
from typing import Any

import chromadb
from dagster import ConfigurableResource
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

logger = logging.getLogger(__name__)


def get_chroma_client(
    host: str | None = None,
    port: int | None = None,
    persistent_path: str = "./chroma_data",
) -> chromadb.ClientAPI:
    """
    Connect to ChromaDB:
    1. Tries configured host/port (e.g. 'chromadb:8000').
    2. If unreachable, tries local host port 'localhost:8002' (mapped in docker-compose.yaml).
    3. Tries 'localhost:8000'.
    4. Falls back to PersistentClient at persistent_path.
    """
    target_host = host or os.getenv("CHROMA_HOST", "chromadb")
    raw_port = port if port is not None else os.getenv("CHROMA_PORT", "8000")
    target_port = int(raw_port)

    # 1. Try primary target
    try:
        client = chromadb.HttpClient(host=target_host, port=target_port)
        client.heartbeat()
        logger.info(f"Connected to ChromaDB at {target_host}:{target_port}")
        return client
    except Exception as e:
        logger.debug(f"Chroma primary connection to {target_host}:{target_port} failed ({e})")

    # 2. Try host mapped port (8002) if running locally outside docker network
    for trial_host, trial_port in [("localhost", 8002), ("127.0.0.1", 8002), ("localhost", 8000)]:
        try:
            client = chromadb.HttpClient(host=trial_host, port=trial_port)
            client.heartbeat()
            logger.info(f"Connected to ChromaDB on fallback {trial_host}:{trial_port}")
            return client
        except Exception:
            continue

    # 3. Fallback to local PersistentClient
    storage_path = os.getenv("CHROMA_PERSISTENT_DIR", persistent_path)
    logger.info(f"ChromaDB HttpClient unavailable, using local PersistentClient at '{storage_path}'.")
    return chromadb.PersistentClient(path=storage_path)


class ChromaResource(ConfigurableResource):
    """
    Resource managing ChromaDB connections and collection upserts.
    """

    host: str = "chromadb"
    port: int = 8000
    persistent_path: str = "./chroma_data"

    def _get_client(self) -> chromadb.ClientAPI:
        return get_chroma_client(
            host=self.host,
            port=self.port,
            persistent_path=self.persistent_path,
        )

    def upsert_chunks(self, collection_name: str, chunks: list[dict[str, Any]]) -> int:
        """
        Upsert document chunks into the target ChromaDB collection.
        Purges prior chunks for all article_ids in the batch first to guarantee idempotency.
        """
        if not chunks:
            return 0

        client = self._get_client()
        col = client.get_or_create_collection(name=collection_name)

        # Clean prior chunks for all articles present in this batch
        article_ids = {
            str(c.get("metadata", {}).get("article_id"))
            for c in chunks
            if c.get("metadata", {}).get("article_id")
        }
        for aid in article_ids:
            try:
                col.delete(where={"article_id": aid})
            except Exception as e:
                logger.debug(f"ChromaResource: Note during prior chunk purge for {aid}: {e}")

        ids = [c["id"] for c in chunks]
        documents = [c["document"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # Chroma supports batch addition
        batch_size = 500
        for i in range(0, len(chunks), batch_size):
            col.add(
                ids=ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        logger.info(f"ChromaResource: Upserted {len(chunks)} chunks into '{collection_name}'.")
        return len(chunks)

    def delete_by_article(self, collection_name: str, article_id: str) -> None:
        """Delete all chunks belonging to an article."""
        client = self._get_client()
        col = client.get_or_create_collection(name=collection_name)
        col.delete(where={"article_id": str(article_id)})
