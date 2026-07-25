import logging
import os
import socket

import chromadb

logger = logging.getLogger(__name__)


def get_chroma_client():
    host = os.getenv("CHROMA_HOST", "chromadb")
    port = int(os.getenv("CHROMA_PORT", 8000))

    try:
        socket.gethostbyname(host)
    except socket.gaierror:
        host = "localhost"
        port = 8002

    try:
        client = chromadb.HttpClient(host=host, port=port)
        collection = client.get_or_create_collection(name="articles")
        logger.info(f"ChromaDB client initialized successfully on {host}:{port}.")
        return client, collection
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB client: {e}")
        return None, None


chroma_client, articles_collection = get_chroma_client()

