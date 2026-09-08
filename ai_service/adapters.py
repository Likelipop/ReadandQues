"""
ai_service/adapters.py — Dependency injection for external service access.

Resolves broken imports between ai_service and Django service layer
by providing a unified import mechanism with clear fallback chain.
"""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_article_store = None


def get_article_store() -> Any | None:
    """Lazily resolve article_store from available import paths."""
    global _article_store
    if _article_store is not None:
        return _article_store

    for module_path in [
        "service.infrastructure.mongo.article_store",
        "ReadAndQues.service.infrastructure.mongo.article_store",
    ]:
        try:
            _article_store = importlib.import_module(module_path)
            logger.debug(f"[adapters] Successfully imported article_store from {module_path}")
            return _article_store
        except ImportError:
            continue

    logger.warning("[adapters] Could not import article_store from any known path.")
    return None


def get_mongo_client() -> Any | None:
    """Lazily resolve MongoDB client from article_store."""
    store = get_article_store()
    if store and hasattr(store, "get_mongo_client"):
        try:
            return store.get_mongo_client()
        except Exception as e:
            logger.debug(f"[adapters] Could not get mongo client: {e}")
    return None
