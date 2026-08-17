import logging

from pymongo.database import Database
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)


def safe_create_index(coll, keys, **kwargs):
    try:
        coll.create_index(keys, **kwargs)
    except OperationFailure as e:
        if "IndexOptionsConflict" in str(e) or e.code == 85:
            logger.warning(f"Index on {keys} already exists with different options/name: {e}")
        else:
            raise


def apply(db: Database) -> None:
    """
    Applies initial MongoDB validators and indexes for articles, attempts, and tracking collections.
    """
    logger.info("Applying 0001_initial_mongo_validators_and_indexes...")

    articles = db["gold_articles"]
    safe_create_index(articles, "article_id", name="idx_article_id")
    safe_create_index(articles, "url", name="idx_article_url")
    safe_create_index(articles, [("status", 1), ("created_at", -1)], name="idx_status_created")
    safe_create_index(articles, "user_id", name="idx_user_id")

    attempts = db["attempts"]
    safe_create_index(attempts, [("user_id", 1), ("article_id", 1)], name="idx_user_article_attempt")
    safe_create_index(attempts, "submitted_at", name="idx_submitted_at")

    history = db["reading_history"]
    safe_create_index(history, [("user_id", 1), ("article_id", 1)], name="idx_user_article_history")

    highlights = db["user_highlights"]
    safe_create_index(highlights, [("user_id", 1), ("article_id", 1)], name="idx_user_article_highlight")

    sections = db["homepage_sections"]
    safe_create_index(sections, "section_id", unique=True, name="idx_section_id_unique")

    vocab = db["vocab_tracking"]
    safe_create_index(vocab, [("user_id", 1), ("word", 1)], name="idx_user_word_vocab")

    logger.info("0001_initial_mongo_validators_and_indexes completed.")
