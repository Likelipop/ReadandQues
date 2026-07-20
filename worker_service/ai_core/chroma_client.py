import chromadb
import logging

logger = logging.getLogger(__name__)

# Initialize ChromaDB client connecting to the docker container
try:
    chroma_client = chromadb.HttpClient(host='localhost', port=8002)
    # Get or create the collection for articles
    articles_collection = chroma_client.get_or_create_collection(name="articles")
    logger.info("ChromaDB client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB client: {e}")
    chroma_client = None
    articles_collection = None
