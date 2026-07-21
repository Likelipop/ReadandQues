"""
worker_service/database/Chroma/connection.py — Standalone ChromaDB connection.

Connects to ChromaDB vector store.
"""

import chromadb
import logging

logger = logging.getLogger(__name__)

def get_chroma_client():
    try:
        client = chromadb.HttpClient(host='localhost', port=8002)
        collection = client.get_or_create_collection(name="articles")
        logger.info("ChromaDB client initialized successfully.")
        return client, collection
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB client: {e}")
        return None, None

chroma_client, articles_collection = get_chroma_client()
